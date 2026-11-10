import { expect, test } from '@playwright/test';

const receipt = {
  name: 'receipt.png',
  mimeType: 'image/png',
  buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC', 'base64'),
};
const task = {
  id: 'review-1', status: 'PENDING', fee_cents: 75,
  proposed_value: '32.10', reviewer_value: null, crop_url: '/uploads/test.png',
};
const batch = {
  id: 'batch-1', data_mode: 'live', payment_status: 'NOT_STARTED',
  budget_cents: 500, captured_cents: 0, tasks: [], documents: [], events: [],
};

// Hold a response until the test has observed the in-flight UI.
function pendingResponse() {
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  return { pending, release };
}

test.beforeEach(async ({ page }) => {
  await page.route('**/api/**', route => route.abort());
  await page.route('https://**', route => route.abort());
  await page.route('**/uploads/*.png', route => route.fulfill({ contentType: 'image/png', body: receipt.buffer }));
});

test('reviewer click posts the correction once and shows SUBMITTED after success', async ({ page }) => {
  const response = pendingResponse();
  const submissions = [];
  let saved = task;
  await page.route('**/api/tasks/review-1', route => route.fulfill({ json: saved }));
  await page.route('**/api/tasks/review-1/submit', async route => {
    submissions.push([route.request().method(), route.request().postDataJSON()]);
    await response.pending;
    saved = { ...task, status: 'SUBMITTED', reviewer_value: '32.40' };
    await route.fulfill({ json: { ok: true, status: saved.status } });
  });
  await page.goto('/review/review-1?token=test-token');
  await page.getByRole('textbox').fill('32.40');
  await page.getByRole('button', { name: 'Submit verification' }).click();
  try {
    await expect(page.getByRole('button', { name: 'Submitting…' })).toBeDisabled();
    await expect.poll(() => submissions).toEqual([['POST', { token: 'test-token', value: '32.40' }]]);
    await expect(page.getByText('SUBMITTED', { exact: true })).toHaveCount(0);
  } finally {
    response.release();
  }
  await expect(page.getByText('SUBMITTED', { exact: true })).toBeVisible();
  expect(submissions).toHaveLength(1);
});

test('reviewer can correct a rejected total and submit with Enter', async ({ page }) => {
  let saved = task;
  await page.route('**/api/tasks/review-1', route => route.fulfill({ json: saved }));
  await page.route('**/api/tasks/review-1/submit', route => {
    const { value } = route.request().postDataJSON();
    if (value === 'oops') return route.fulfill({ status: 400, json: { detail: 'Enter a valid numeric total' } });
    saved = { ...task, status: 'SUBMITTED', reviewer_value: value };
    return route.fulfill({ json: { ok: true, status: saved.status } });
  });
  await page.goto('/review/review-1?token=test-token');
  const input = page.getByRole('textbox');
  await input.fill('oops');
  await page.getByRole('button', { name: 'Submit verification' }).click();
  await expect(page.getByRole('alert')).toContainText('Enter a valid numeric total');
  await expect(page.getByText('PENDING', { exact: true })).toBeVisible();
  await input.fill('32.40');
  await input.press('Enter');
  await expect(page.getByText('SUBMITTED', { exact: true })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('Analyze clicks upload the selected file and a failed analysis can be retried with Enter', async ({ page }) => {
  const response = pendingResponse();
  const uploads = [];
  await page.route('**/api/config', route => route.fulfill({ json: { gemini_enabled: true } }));
  await page.route('**/api/batches', route => route.fulfill({ json: batch }));
  await page.route('**/api/batches/batch-1/documents', async route => {
    const request = route.request();
    const body = new Response(request.postDataBuffer(), { headers: request.headers() });
    const file = (await body.formData()).get('file');
    uploads.push([request.method(), file.name, file.type, Buffer.from(await file.arrayBuffer())]);
    if (uploads.length === 1) {
      await response.pending;
      return route.fulfill({ status: 502, json: { detail: 'Gemini extraction failed' } });
    }
    return route.fulfill({ json: { ...batch, documents: [{
      id: 'doc-1', filename: receipt.name, image_url: '/uploads/test.png', first: { merchant: 'Test receipt' },
    }] } });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'New live batch' }).click();
  const analyze = page.getByRole('button', { name: 'Analyze', exact: true });
  await expect(analyze).toBeDisabled();
  await page.locator('input[type=file]').setInputFiles(receipt);
  await analyze.click();
  const expectedUpload = ['POST', receipt.name, receipt.mimeType, receipt.buffer];
  try {
    await expect(page.getByRole('button', { name: 'Analyzing…' })).toBeDisabled();
    await expect.poll(() => uploads).toEqual([expectedUpload]);
  } finally {
    response.release();
  }
  await expect(page.getByRole('alert')).toContainText('Gemini extraction failed');
  await expect(page.getByText('Test receipt', { exact: true })).toHaveCount(0);
  await expect(analyze).toBeEnabled();
  await analyze.press('Enter');
  await expect(page.getByRole('status')).toContainText(receipt.name);
  await expect(page.getByText('Test receipt', { exact: true })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(analyze).toBeDisabled();
  await expect(page.locator('input[type=file]')).toHaveValue('');
  expect(uploads).toEqual([expectedUpload, expectedUpload]);
});
