#!/usr/bin/env python3
"""
Debug embedded dashboard loading
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_embedded():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()

        # Collect console messages
        console_logs = []
        page.on('console', lambda msg: console_logs.append({
            'type': msg.type,
            'text': msg.text,
            'location': msg.location
        }))

        # Collect network errors
        network_errors = []
        page.on('requestfailed', lambda req: network_errors.append({
            'url': req.url,
            'failure': req.failure
        }))

        # Navigate directly to embedded dashboard URL
        url = "http://localhost:8088/dashboard/12/embedded?guest_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjp7InVzZXJuYW1lIjoiXHU1NWI2XHU2OTZkXHU5MGU4XHUzMGU2XHUzMGZjXHUzMGI2XHUzMGZjIiwiZmlyc3RfbmFtZSI6Ikd1ZXN0IiwibGFzdF9uYW1lIjoiVXNlciJ9LCJyZXNvdXJjZXMiOlt7InR5cGUiOiJkYXNoYm9hcmQiLCJpZCI6IjdhYWFiYzAzLTJjNDctNDU0MC04MjMzLWYyMmJiZGIyY2M4MSJ9XSwicmxzIjpbeyJjbGF1c2UiOiJkZXBhcnRtZW50X2lkID0gMTAxIn1dLCJleHAiOjE3NjgxODQ3MTZ9.K2vybhSa0Bl5RnIErUQXLL-_1w3YoCr6XPzwOMTh-sw"

        print(f"Loading embedded dashboard directly: {url[:100]}...")
        await page.goto(url, wait_until='networkidle', timeout=30000)

        # Wait for potential loading
        await page.wait_for_timeout(10000)

        # Take screenshot
        await page.screenshot(path="/Users/kazu/coding/research-superset/direct_embedded.png", full_page=True)

        # Check page content
        body_text = await page.locator('body').inner_text()
        print("\n=== Page Body Text (first 1000 chars) ===")
        print(body_text[:1000])

        # Check for specific elements
        print("\n=== Checking for elements ===")

        app_div = await page.query_selector('#app')
        if app_div:
            print("✓ Found #app div")
            data_bootstrap = await app_div.get_attribute('data-bootstrap')
            if data_bootstrap:
                print(f"✓ Found data-bootstrap attribute (length: {len(data_bootstrap)})")
                # Check if it contains embedded info
                if 'embedded' in data_bootstrap:
                    print("✓ data-bootstrap contains 'embedded'")
                if 'dashboard_id' in data_bootstrap:
                    print("✓ data-bootstrap contains 'dashboard_id'")
        else:
            print("✗ No #app div found")

        # Console logs
        print(f"\n=== Console Logs ({len(console_logs)} total) ===")
        for log in console_logs[:20]:
            print(f"[{log['type']}] {log['text']}")

        # Network errors
        if network_errors:
            print(f"\n=== Network Errors ({len(network_errors)} total) ===")
            for err in network_errors[:10]:
                print(f"Failed: {err['url']}")
                print(f"  Reason: {err['failure']}")

        await browser.close()
        print("\n✓ Direct embedded screenshot saved to: /Users/kazu/coding/research-superset/direct_embedded.png")

if __name__ == "__main__":
    asyncio.run(debug_embedded())
