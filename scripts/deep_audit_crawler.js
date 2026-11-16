const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://127.0.0.1:8000';
const FRONTEND_DIR = path.resolve(__dirname, '../frontend');

const pages = fs.readdirSync(FRONTEND_DIR)
  .filter(f => f.endsWith('.html'))
  .sort();

console.log(`Auditing ${pages.length} HTML pages on ${BASE_URL}...`);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const pageName of pages) {
    const pageUrl = `${BASE_URL}/${pageName}`;
    const pageObj = await browser.newPage();
    
    const errors = [];
    const failedRequests = [];

    // Capture console errors
    pageObj.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Ignore Google Analytics 4 blocked or third-party tracking block errors in headless
        if (!text.includes('googletagmanager') && !text.includes('google-analytics')) {
          errors.push(`Console Error: ${text}`);
        }
      }
    });

    // Capture unhandled page errors
    pageObj.on('pageerror', err => {
      errors.push(`Page Error: ${err.message}`);
    });

    // Capture failed network requests
    pageObj.on('response', resp => {
      const status = resp.status();
      const url = resp.url();
      if (status >= 400 && !url.includes('google-analytics') && !url.includes('googletagmanager')) {
        failedRequests.push(`${status} on ${url}`);
      }
    });

    // Set mock user for dashboard & admin pages to test authenticated state as well
    if (pageName === 'dashboard.html' || pageName === 'admin.html') {
      await pageObj.addInitScript(() => {
        localStorage.setItem('mlops_user', JSON.stringify({
          name: 'Lead Architect',
          email: 'demo@nodepilot.dev',
          role: 'admin',
          is_admin: true,
          token: 'demo'
        }));
        localStorage.setItem('mlops_token', 'demo');
      });
    }

    try {
      const resp = await pageObj.goto(pageUrl, { waitUntil: 'load', timeout: 15000 });
      await pageObj.waitForTimeout(500); // Wait for microtasks

      // Check broken images (excluding streaming map tiles from CartoCDN / Leaflet)
      const brokenImages = await pageObj.evaluate(() => {
        const imgs = Array.from(document.querySelectorAll('img:not(.leaflet-tile)'));
        return imgs
          .filter(img => !img.src.includes('basemaps.cartocdn.com'))
          .filter(img => !img.complete || img.naturalWidth === 0)
          .map(img => img.src || img.getAttribute('src'));
      });

      // Check broken internal anchor links
      const brokenInternalLinks = await pageObj.evaluate((allPages) => {
        const links = Array.from(document.querySelectorAll('a[href]'));
        const issues = [];
        for (const a of links) {
          const href = a.getAttribute('href');
          if (href && href.endsWith('.html') && !href.startsWith('http') && !href.startsWith('//')) {
            const clean = href.split('#')[0].split('?')[0];
            if (clean && !allPages.includes(clean)) {
              issues.push(`Broken link to: ${href}`);
            }
          }
        }
        return issues;
      }, pages);

      results.push({
        page: pageName,
        status: resp ? resp.status() : 'NO_RESPONSE',
        errors,
        failedRequests,
        brokenImages,
        brokenInternalLinks
      });
    } catch (ex) {
      results.push({
        page: pageName,
        status: 'FAILED_TO_LOAD',
        errors: [`Exception: ${ex.message}`],
        failedRequests,
        brokenImages: [],
        brokenInternalLinks: []
      });
    } finally {
      await pageObj.close();
    }
  }

  await browser.close();

  // Print Summary
  console.log('\n========================================================');
  console.log('              COMPREHENSIVE AUDIT REPORT                ');
  console.log('========================================================\n');
  
  let totalIssues = 0;
  for (const r of results) {
    const hasIssues = r.errors.length > 0 || r.failedRequests.length > 0 || r.brokenImages.length > 0 || r.brokenInternalLinks.length > 0;
    if (hasIssues) {
      totalIssues++;
      console.log(`❌ [FAIL] ${r.page} (HTTP ${r.status})`);
      r.errors.forEach(e => console.log(`   - ${e}`));
      r.failedRequests.forEach(f => console.log(`   - Failed Req: ${f}`));
      r.brokenImages.forEach(img => console.log(`   - Broken Img: ${img}`));
      r.brokenInternalLinks.forEach(l => console.log(`   - ${l}`));
    } else {
      console.log(`✅ [PASS] ${r.page} (HTTP ${r.status})`);
    }
  }

  console.log('\n--------------------------------------------------------');
  console.log(`Total Pages: ${results.length} | Pages with Issues: ${totalIssues}`);
  console.log('========================================================\n');
})();
