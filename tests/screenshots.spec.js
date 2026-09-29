const { test } = require('@playwright/test');

test('Family Operations screenshots', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' });

  await page.screenshot({
    path: 'docs/screenshots/01-home.png',
    fullPage: true
  });

  const points = page.getByRole('link', { name: /points/i }).first();
  if (await points.isVisible().catch(() => false)) {
    await points.click();
    await page.waitForLoadState('networkidle');
    await page.screenshot({
      path: 'docs/screenshots/02-points.png',
      fullPage: true
    });
  }
});
