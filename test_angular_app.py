#!/usr/bin/env python3
"""
Test Angular + Nest.js + Superset Embedded SDK integration
"""
import asyncio
from playwright.async_api import async_playwright

async def test_app():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1400, 'height': 1000})
        page = await context.new_page()

        # Collect console messages
        console_logs = []
        page.on('console', lambda msg: console_logs.append({
            'type': msg.type,
            'text': msg.text
        }))

        # Navigate to Angular app
        url = "http://localhost:4200"
        print(f"Loading Angular app: {url}")
        await page.goto(url, wait_until='networkidle', timeout=60000)

        # Wait for dashboard to load
        print("Waiting for dashboard to load...")
        await page.wait_for_timeout(15000)

        # Take screenshot
        await page.screenshot(path="/Users/kazu/coding/research-superset/angular-app-initial.png", full_page=True)
        print("✓ Initial screenshot saved: angular-app-initial.png")

        # Check for department tabs
        tabs = await page.query_selector_all('.tab-button')
        print(f"\n✓ Found {len(tabs)} department tabs")

        # Click on each department and take screenshots
        departments = ['営業部', '開発部', 'マーケティング部']
        for i, dept_name in enumerate(departments):
            if i < len(tabs):
                print(f"\nClicking on {dept_name} tab...")
                await tabs[i].click()
                await page.wait_for_timeout(10000)  # Wait for dashboard to load

                screenshot_path = f"/Users/kazu/coding/research-superset/angular-app-{dept_name}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"✓ Screenshot saved: angular-app-{dept_name}.png")

        # Print console logs
        print(f"\n=== Console Logs ({len(console_logs)} total) ===")
        for log in console_logs[:30]:
            print(f"[{log['type']}] {log['text']}")

        # Check for Superset dashboard container
        dashboard_container = await page.query_selector('#superset-dashboard')
        if dashboard_container:
            print("\n✓ Superset dashboard container found")
        else:
            print("\n✗ Superset dashboard container NOT found")

        await browser.close()
        print("\n✓ Testing complete!")

if __name__ == "__main__":
    asyncio.run(test_app())
