const { test, expect } = require('@playwright/test');

test.describe('Landing Page UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('Homepage loads and displays primary heading', async ({ page }) => {
    await expect(page).toHaveTitle(/MLOps\.dev/);
    
    // Check heading from hero section
    const heading = page.locator('.hero-h');
    await expect(heading).toBeVisible();
  });

  test('Navigation bar becomes sticky on scroll', async ({ page }) => {
    const nav = page.locator('#nav');
    
    // Scroll down 200 pixels
    await page.evaluate(() => window.scrollBy(0, 200));
    
    // Wait for the class to be applied on scroll
    await page.waitForFunction(() => {
      const navEl = document.querySelector('#nav');
      return navEl && navEl.classList.contains('scrolled');
    });
    
    // Nav should gain the "scrolled" class for glassmorphism
    await expect(nav).toHaveClass(/scrolled/);
  });

  test('Motion engine is loaded', async ({ page }) => {
    // Check if the script is in the DOM
    const motionScript = page.locator('script[src="/motion.js"]');
    await expect(motionScript).toBeAttached();
  });

  test('Primary CTA buttons exist and are styled correctly', async ({ page }) => {
    const primaryBtn = page.locator('.cta-primary').first();
    await expect(primaryBtn).toBeVisible();
    
    // Check computed styles to ensure the CSS is loaded properly
    const bg = await primaryBtn.evaluate((el) => window.getComputedStyle(el).backgroundColor);
    // #4F7FEF is rgb(79, 127, 239)
    expect(bg).toBe('rgb(79, 127, 239)');
  });
});

test.describe('Dashboard UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard.html');
  });

  test('Dashboard loads the auth screen initially', async ({ page }) => {
    const authScreen = page.locator('#auth-screen');
    await expect(authScreen).toBeVisible();
  });

  test('Dark mode default styling applies correctly', async ({ page }) => {
    const authWrap = page.locator('.auth-wrap');
    await expect(authWrap).toBeVisible();
    
    // Check if the background color of body is dark.
    // By default body background is var(--ink) which is #080B14 rgb(8, 11, 20).
    const bodyBg = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor);
    expect(bodyBg).toBe('rgb(8, 11, 20)');
  });
});
