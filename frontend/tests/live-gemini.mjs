// Opt-in: node tests/live-gemini.mjs from frontend. Uses two real Gemini requests.
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { chromium, expect } from '@playwright/test';
import { createServer } from 'vite';

const dir = await mkdtemp(join(tmpdir(), 'humanbridge-live-'));
const db = join(dir, 'live.db');
const api = 'http://127.0.0.1:18176';
const server = spawn('python', ['-m','uvicorn','api:app','--host','127.0.0.1','--port','18176','--no-access-log'], {
  cwd: '../backend', windowsHide: true, stdio: 'ignore',
  env: {...process.env, DB_PATH: db, UPLOAD_DIR: join(dir,'uploads')},
});
let browser, vite;
try {
  for (let i=0; i<150; i++) {
    if (server.exitCode !== null) throw Error('Isolated API failed to start');
    if ((await fetch(api+'/api/health').catch(()=>null))?.ok) break;
    await delay(100);
  }
  vite = await createServer({server:{host:'127.0.0.1',port:14176,strictPort:true,proxy:{'/api':api,'/uploads':api}}});
  await vite.listen();
  browser = await chromium.launch({channel:'chrome'});
  const page = await browser.newPage({baseURL:'http://127.0.0.1:14176'});
  await page.route('https://**', r=>r.abort());
  await page.goto('http://127.0.0.1:14176');
  await page.getByRole('button',{name:'New live batch'}).click();
  const sample = await page.request.get('/api/sample-receipt');
  assert.equal(sample.status(),200);
  await page.getByLabel('Choose a receipt image').setInputFiles({name:'sample-stationery.png',mimeType:'image/png',buffer:await sample.body()});
  const result = page.waitForResponse(r=>r.url().endsWith('/documents'),{timeout:270000});
  await page.getByRole('button',{name:'Analyze',exact:true}).click();
  const response = await result;
  const batch = await response.json();
  if (!response.ok()) throw Error(batch.detail);
  const [doc] = batch.documents;
  assert.equal(doc.mode,'LIVE_GEMINI');
  const raw = JSON.parse(execFileSync('python',['-c',
    "import json,sqlite3,sys; print(json.dumps([json.loads(json.loads(r[0])['raw']) for r in sqlite3.connect(sys.argv[1]).execute('SELECT evidence FROM extraction_passes ORDER BY number')]))",db],{encoding:'utf8'}));
  assert.deepEqual(raw,[doc.first,doc.second]);
  await page.reload();
  for (const field of ['merchant','date','currency','subtotal','tax','total']) {
    const cells = page.getByRole('row').filter({has:page.getByRole('rowheader',{name:field,exact:true})}).getByRole('cell');
    for (const [i,reading] of raw.entries()) await expect(cells.nth(i)).toHaveText(reading[field] ?? 'Unavailable');
  }
  console.log(JSON.stringify({batch:batch.id,document:doc.id,passes:doc.passes,readings:raw,findings:doc.reasons,database:db},null,2));
} finally {
  await browser?.close();
  await vite?.close();
  server.kill();
}
