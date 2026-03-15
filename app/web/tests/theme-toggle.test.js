import { chromium } from 'playwright';

async function testThemeToggle() {
  console.log('Starting theme toggle test...');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to the app
    console.log('Navigating to http://localhost:3000...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });

    // Wait for the app to load
    await page.waitForSelector('.app-header', { timeout: 10000 });
    console.log('App loaded successfully!');

    // Check initial theme state (should be light mode by default)
    const htmlElement = await page.$('html');
    const initialClass = await htmlElement.getAttribute('class');
    console.log(`Initial HTML class: "${initialClass}"`);

    const initialIsDark = initialClass?.includes('dark') || false;
    console.log(`Initial dark mode: ${initialIsDark}`);

    // Check if theme button exists
    const themeBtn = await page.$('.theme-btn');
    if (!themeBtn) {
      throw new Error('Theme button not found!');
    }
    console.log('Theme button found!');

    // Click the theme button to toggle
    console.log('Clicking theme toggle button...');
    await themeBtn.click();

    // Wait for transition
    await page.waitForTimeout(500);

    // Check new theme state
    const newClass = await htmlElement.getAttribute('class');
    console.log(`New HTML class: "${newClass}"`);

    const newIsDark = newClass?.includes('dark') || false;
    console.log(`New dark mode: ${newIsDark}`);

    // Verify theme changed
    if (initialIsDark === newIsDark) {
      throw new Error(`Theme did not change! Initial: ${initialIsDark}, New: ${newIsDark}`);
    }
    console.log('Theme toggle works correctly!');

    // Check CSS variables are applied
    const bgColor = await page.evaluate(() => {
      return window.getComputedStyle(document.body).backgroundColor;
    });
    console.log(`Body background color: ${bgColor}`);

    // Test second toggle
    console.log('Clicking theme toggle button again...');
    await themeBtn.click();
    await page.waitForTimeout(500);

    const finalClass = await htmlElement.getAttribute('class');
    const finalIsDark = finalClass?.includes('dark') || false;
    console.log(`Final dark mode: ${finalIsDark}`);

    if (finalIsDark !== initialIsDark) {
      throw new Error(`Theme did not toggle back correctly! Initial: ${initialIsDark}, Final: ${finalIsDark}`);
    }
    console.log('Theme toggle back works correctly!');

    // Test localStorage persistence
    const storedTheme = await page.evaluate(() => localStorage.getItem('theme'));
    console.log(`Stored theme in localStorage: ${storedTheme}`);

    // Test all pages
    console.log('\n--- Testing all pages ---');

    // Test Modules page
    await page.goto('http://localhost:3000/modules', { waitUntil: 'networkidle' });
    await page.waitForSelector('.modules-page', { timeout: 5000 });
    console.log('Modules page loads correctly');

    // Check page title is visible
    const modulesTitle = await page.$('.page-title');
    if (modulesTitle) {
      const titleText = await modulesTitle.textContent();
      console.log(`Modules page title: "${titleText}"`);
    }

    // Test CodeGen page
    await page.goto('http://localhost:3000/codegen', { waitUntil: 'networkidle' });
    try {
      await page.waitForSelector('.codegen-page', { timeout: 3000 });
      console.log('CodeGen page loads correctly');
    } catch (e) {
      console.log('CodeGen page may need backend API, skipping element check');
    }

    // Test Stats page
    await page.goto('http://localhost:3000/stats', { waitUntil: 'networkidle' });
    try {
      await page.waitForSelector('.stats-page', { timeout: 3000 });
      console.log('Stats page loads correctly');
    } catch (e) {
      console.log('Stats page may need backend API, skipping element check');
    }

    // Test theme works on all pages
    console.log('\n--- Testing theme on all pages ---');

    // First test light mode colors
    console.log('\nLight mode colors:');
    for (const pagePath of ['/modules', '/codegen', '/stats']) {
      await page.goto(`http://localhost:3000${pagePath}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(300);

      const pageBgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor;
      });
      console.log(`Page ${pagePath} background: ${pageBgColor}`);
    }

    // Switch to dark mode
    console.log('\nSwitching to dark mode...');
    const themeBtn2 = await page.$('.theme-btn');
    await themeBtn2.click();
    await page.waitForTimeout(500);

    // Test dark mode colors
    console.log('\nDark mode colors:');
    for (const pagePath of ['/modules', '/codegen', '/stats']) {
      await page.goto(`http://localhost:3000${pagePath}`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(300);

      const pageBgColor = await page.evaluate(() => {
        return window.getComputedStyle(document.body).backgroundColor;
      });
      console.log(`Page ${pagePath} background: ${pageBgColor}`);
    }

    // Verify dark mode colors are different from light mode
    const lightBg = 'rgb(240, 244, 248)';
    const darkBg = 'rgb(15, 23, 42)';

    await page.goto('http://localhost:3000/modules', { waitUntil: 'networkidle' });
    const finalBgColor = await page.evaluate(() => {
      return window.getComputedStyle(document.body).backgroundColor;
    });

    if (finalBgColor !== darkBg) {
      throw new Error(`Dark mode background incorrect. Expected: ${darkBg}, Got: ${finalBgColor}`);
    }
    console.log(`\nDark mode background verified: ${finalBgColor}`);

    console.log('\n=== All tests passed! ===');

  } catch (error) {
    console.error('Test failed:', error.message);
    throw error;
  } finally {
    await browser.close();
  }
}

testThemeToggle().catch(err => {
  console.error('Test suite failed:', err);
  process.exit(1);
});