import { expect, test } from '@playwright/test';

for (const width of [390, 1280]) {
  test(`evaluation and primary action fit at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto('/');
    await expect(page.getByRole('button', { name: 'New live batch' })).toBeVisible();
    await page.locator('summary').filter({ hasText: 'Synthetic evaluation' }).press('Enter');
    await expect(page.getByText(/AI-assisted visual readings/)).toBeVisible();
    const contentWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(contentWidth).toBeLessThanOrEqual(width);
  });
}
