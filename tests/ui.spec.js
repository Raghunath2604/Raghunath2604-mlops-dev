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
    
    // Scroll down 200 pixels with instant behavior to trigger the scroll handler immediately
    await page.evaluate(() => {
      window.scrollTo({ top: 200, behavior: 'instant' });
      window.dispatchEvent(new Event('scroll'));
    });
    
    // Wait for the class to be applied on scroll
    await page.waitForFunction(() => {
      const navEl = document.querySelector('#nav');
      return navEl && navEl.classList.contains('scrolled');
    }, null, { timeout: 5000 });
    
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

test.describe('Dashboard UI & Access Control', () => {
  test('Unauthenticated dashboard access enforces air-gapped RBAC clearance redirect', async ({ page }) => {
    await page.goto('/dashboard.html');
    await expect(page).toHaveURL(/login\.html\?notice=admin_clearance_required/);
    const authStage = page.locator('.auth-stage-container');
    await expect(authStage).toBeVisible();
  });

  test('Authenticated operator loads fleet control plane and silicon metrics', async ({ page }) => {
    await page.goto('/login.html');
    await page.evaluate(() => {
      localStorage.setItem('mlops_user', JSON.stringify({
        name: 'Lead Architect',
        email: 'demo@nodepilot.dev',
        role: 'admin',
        is_admin: true,
        token: 'demo'
      }));
      localStorage.setItem('mlops_token', 'demo');
    });
    await page.goto('/dashboard.html');
    const appEl = page.locator('#app');
    await expect(appEl).toBeVisible();
    
    // Check dark mode background (--bg-base #06090e -> rgb(6, 9, 14))
    const bodyBg = await page.evaluate(() => window.getComputedStyle(document.body).backgroundColor);
    expect(bodyBg).toBe('rgb(6, 9, 14)');

    // Verify KPIs
    const totalDevices = page.locator('#k-total');
    await expect(totalDevices).toBeVisible();
  });
});

