import { test, expect } from '@playwright/test';

const batch = {id:'batch-one', payment_status:'AWAITING_BUYER', budget_cents:500, captured_cents:0,
  tasks:[],documents:[],events:[],paypal_order_id:'ORDER-TEST',
  paypal_approval_url:'https://www.sandbox.paypal.com/checkoutnow?token=ORDER-TEST'};

async function checkout(page, callback, providerStatus) {
  let current = batch;
  const calls = {checks:0,authorizations:0};
  await page.addInitScript(() => localStorage.setItem('humanbridge_last_batch','batch-one'));
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname==='/api/config') return route.fulfill({json:{}});
    if (url.pathname==='/api/batches/batch-one') return route.fulfill({json:current});
    if (url.pathname.endsWith('/approval')) {
      expect(url.searchParams.get('token')).toBe(batch.paypal_order_id);
      calls.checks++;
      return route.fulfill({json:{status:providerStatus}});
    }
    if (url.pathname.endsWith('/authorize')) {
      expect(providerStatus).toBe('APPROVED');
      calls.authorizations++;
      current={...batch,payment_status:'AUTHORIZED',verified_cents:500,auth_currency:'USD'};
      return route.fulfill({json:current});
    }
    throw Error('Unexpected checkout request: '+url.pathname);
  });
  await page.goto('/?'+callback);
  return calls;
}

test('approved return verifies the bound order before authorization', async ({page})=>{
  const calls=await checkout(page,'checkout=return&batch=batch-one&token=ORDER-TEST','APPROVED');
  await expect(page.getByRole('status')).toContainText('Buyer approved');
  expect(calls.authorizations).toBe(0);
  await page.getByRole('button',{name:'Authorize approved budget'}).click();
  await expect(page.getByText('Authorization verified for $5.00 USD.')).toBeVisible();
  await page.reload();
  await expect(page.getByText('Authorization verified for $5.00 USD.')).toBeVisible();
  expect(calls.authorizations).toBe(1);
});

test('cancelled checkout can reopen the exact existing provider link', async ({page})=>{
  const calls=await checkout(page,'checkout=cancel&token=ORDER-TEST','PAYER_ACTION_REQUIRED');
  await expect(page.getByRole('status')).toContainText('Buyer cancelled checkout');
  await page.route(batch.paypal_approval_url,route=>route.fulfill({body:'Sandbox test destination'}));
  await page.getByRole('link',{name:'Open Sandbox checkout'}).click();
  await expect(page).toHaveURL(batch.paypal_approval_url);
  expect(calls.authorizations).toBe(0);
});

test('return without approval remains awaiting buyer',async ({page})=>{
  const calls=await checkout(page,'checkout=return&token=ORDER-TEST','PAYER_ACTION_REQUIRED');
  await expect(page.getByRole('status')).toContainText('Awaiting buyer approval');
  await expect(page.getByRole('button',{name:'Authorize approved budget'})).toHaveCount(0);
  expect(calls.authorizations).toBe(0);
});

test('incorrect return token cannot verify or authorize another order',async ({page})=>{
  const calls=await checkout(page,'checkout=return&token=WRONG','APPROVED');
  await expect(page.getByRole('alert')).toContainText('incorrect order token');
  expect(calls).toEqual({checks:0,authorizations:0});
});

test('repeated approval checks are read-only',async ({page})=>{
  const calls=await checkout(page,'checkout=return&token=ORDER-TEST','APPROVED');
  for(let i=0;i<2;i++) await page.getByRole('button',{name:'Check approval status'}).click();
  await expect.poll(()=>calls.checks).toBe(3);
  expect(calls.authorizations).toBe(0);
});

test('expired order gives an explanation without a replacement',async ({page})=>{
  const calls=await checkout(page,'checkout=return&token=ORDER-TEST','EXPIRED');
  await expect(page.getByRole('status')).toContainText('order expired');
  await expect(page.getByRole('link',{name:'Open Sandbox checkout'})).toHaveCount(0);
  expect(calls.authorizations).toBe(0);
});


test('missing PayPal order is identified and cannot open checkout',async ({page})=>{
  const calls=await checkout(page,'checkout=return&token=ORDER-TEST','UNAVAILABLE');
  await expect(page.getByRole('status')).toContainText('PayPal cannot find order ORDER-TEST');
  await expect(page.getByRole('link',{name:'Open Sandbox checkout'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Authorize approved budget'})).toHaveCount(0);
  expect(calls.authorizations).toBe(0);
});
