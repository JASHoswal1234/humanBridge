// Run from frontend after npm run build. Live mode stops at interactive buyer approval.
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium, expect } from '@playwright/test';

const live = process.argv.includes('--live');
const port = live ? 18276 : 18277;
const baseURL = 'http://127.0.0.1:'+port;
const dir = await mkdtemp(join(tmpdir(),'humanbridge-settlement-'));
const profile = join(dir,'chrome');
const python = live ? ['-m','uvicorn','api:app','--host','127.0.0.1','--port',String(port),'--no-access-log'] :
  ['-c', "import sys;sys.path.insert(0,'tests');from settlement_fixture import serve;serve("+port+")"];
if (await fetch(baseURL+'/api/health').catch(()=>null)) throw Error('Test port already in use');
const server = spawn('python',python,{cwd:'../backend',windowsHide:true,detached:live,stdio:'ignore',
  env:{...process.env,DB_PATH:join(dir,'batch.db'),UPLOAD_DIR:join(dir,'uploads'),APP_PUBLIC_URL:baseURL}});
let context, handoff=false;
try {
  for (let i=0;i<150;i++) {
    if(server.exitCode !== null) throw Error('API failed to start');
    if((await fetch(baseURL+'/api/health').catch(()=>null))?.ok) break;
    await delay(100);
  }
  context = await chromium.launchPersistentContext(profile,{channel:'chrome',baseURL});
  const page = await context.newPage();
  await context.route('https://**',r=>r.abort());
  await page.goto('/');
  await page.getByRole('button',{name:'New live batch'}).click();
  const image = execFileSync('python',['-c',"import sys;sys.path.insert(0,'tests');from settlement_fixture import receipt;sys.stdout.buffer.write(receipt())"],{cwd:'../backend'});
  await page.getByLabel('Choose a receipt image').setInputFiles({name:'synthetic-discount.png',mimeType:'image/png',buffer:image});
  const upload = page.waitForResponse(r=>r.url().endsWith('/documents'),{timeout:270000});
  await page.getByRole('button',{name:'Analyze',exact:true}).click();
  const uploaded=await upload;
  const batch=await uploaded.json();
  if(!uploaded.ok()) throw Error(batch.detail);
  if (live && batch.tasks.length === 0) {
    await expect(page.getByRole('button',{name:'Create $5 authorization order'})).toBeDisabled();
    console.log('Live receipt produced no review task. Checkout was unnecessary.');
  } else {
    assert.equal(batch.tasks.length,1,'Expected one actual rule finding on the printed discount receipt');
    console.log('Review findings:',batch.documents[0].reasons);
    const created=page.waitForResponse(r=>r.url().endsWith('/payment/create'));
    await page.getByRole('button',{name:'Create $5 authorization order'}).click();
    const orderResponse=await created;
    const order=await orderResponse.json();
    if(!orderResponse.ok()) throw Error(order.detail);

    if(live) {
      await expect(page.getByRole('link',{name:'Open Sandbox checkout'})).toHaveAttribute('href',order.approval_url,{timeout:60000});
      await expect(page.getByRole('button',{name:'Authorize approved budget'})).toHaveCount(0);
      await page.screenshot({path:join(dir,'awaiting-buyer.png'),fullPage:true});
      console.log(JSON.stringify({order:order.order_id,batch:batch.id,model:batch.documents[0].passes,
        profile,baseURL,directory:dir,serverPid:server.pid}));
      handoff=true;
      server.unref();
    } else {
      await page.getByRole('button',{name:'Authorize approved budget'}).click();
      const opened=context.waitForEvent('page');
      await page.getByRole('button',{name:'Open reviewer'}).click();
      const reviewer=await opened;
      await reviewer.getByRole('textbox').fill('30.00');
      await reviewer.getByRole('button',{name:'Submit verification'}).click();
      await page.getByRole('button',{name:'Request revision'}).click();
      await expect(reviewer.getByRole('textbox')).toBeEnabled({timeout:10000});
      await reviewer.getByRole('textbox').fill('30.39');
      await reviewer.getByRole('button',{name:'Submit verification'}).click();
      const accept=page.getByRole('button',{name:'Accept 30.39'});
      await expect(accept).toBeDisabled();
      await page.getByLabel('Reason for accepting this difference').fill('Printed evidence inspected; approving this service fee.');
      await accept.click();
      await expect(page.getByText(/Requester’s reason:/)).toBeVisible();
      page.once('dialog',dialog=>dialog.accept());
      await page.getByRole('button',{name:/Capture \$0.75/}).click();
      await expect(page.getByText('PayPal confirmed the capture of $0.75.')).toBeVisible();
      await page.reload();
      await expect(page.getByText('CAPTURE-MOCK',{exact:true})).toBeVisible();
      await page.screenshot({path:join(dir,'verified-mock.png'),fullPage:true});
      console.log('PASS browser upload, authorization, revision, resubmission, auto-refresh, acceptance, settlement and reload (mock providers). Screenshot:',join(dir,'verified-mock.png'));
    }
  }
} finally {
  await context?.close();
  if(!handoff) server.kill();
}
