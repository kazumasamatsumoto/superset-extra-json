const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Listen to console logs
  page.on('console', msg => {
    const type = msg.type();
    if (type === 'error' || type === 'warning') {
      console.log(`[${type}] ${msg.text()}`);
    }
  });

  await page.goto('http://localhost:4200');

  console.log('Waiting for dashboard to load...');
  await page.waitForTimeout(8000);

  const departments = [
    { name: '営業部', id: 101, expected: '¥955,000' },
    { name: '開発部', id: 102, expected: '¥835,000' },
    { name: 'マーケティング部', id: 103, expected: '¥240,000' }
  ];

  for (const dept of departments) {
    console.log(`\n=== Testing ${dept.name} (ID: ${dept.id}) ===`);

    // Click the tab
    await page.click(`button:has-text("${dept.name}")`);
    console.log(`Clicked ${dept.name} tab`);

    // Wait for dashboard to update
    await page.waitForTimeout(5000);

    // Take screenshot
    await page.screenshot({
      path: `test-extra-json-${dept.name}.png`,
      fullPage: false
    });
    console.log(`Screenshot saved: test-extra-json-${dept.name}.png`);
    console.log(`Expected total: ${dept.expected}`);
  }

  console.log('\n✅ All tests completed. Check screenshots to verify filtering.');
  console.log('If each department shows different totals matching expected values,');
  console.log('then extra_json filtering is working correctly!');

  await browser.close();
})();
