#!/usr/bin/env python3
"""
Automated browser testing for embedded dashboard
"""
import asyncio
from playwright.async_api import async_playwright
import sys

async def check_embedded_dashboard():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await context.new_page()

        # Navigate to the test page
        url = "http://localhost:8000/test-embedded.html"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until='networkidle', timeout=30000)

        # Wait a bit for iframe to load
        print("Waiting for page to load...")
        await page.wait_for_timeout(5000)

        # Take screenshot
        screenshot_path = "/Users/kazu/coding/research-superset/screenshot.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to: {screenshot_path}")

        # Check for errors in console
        console_messages = []
        page.on('console', lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

        # Get iframe
        iframe_element = await page.query_selector('iframe#dashboard-iframe')
        if iframe_element:
            print("✓ Iframe element found")
            src = await iframe_element.get_attribute('src')
            print(f"  Iframe src: {src[:100]}...")
        else:
            print("✗ Iframe element NOT found")

        # Check page content
        page_content = await page.content()

        # Check for specific text
        if "This page is intended to be embedded" in page_content:
            print("✗ Found 'This page is intended to be embedded' message")
        else:
            print("✓ No iframe warning message found")

        if "You should call configure" in page_content:
            print("✗ Found 'You should call configure' error")
        else:
            print("✓ No configure error found")

        # Get page title
        title = await page.title()
        print(f"Page title: {title}")

        # Try to get iframe content
        try:
            iframe = page.frame_locator('iframe#dashboard-iframe')
            iframe_body = await iframe.locator('body').inner_text(timeout=5000)
            print(f"\nIframe body content (first 500 chars):")
            print(iframe_body[:500])
        except Exception as e:
            print(f"✗ Could not read iframe content: {e}")

        # Check network requests
        print("\nNetwork requests to embedded endpoint:")
        requests = []
        page.on('request', lambda req: requests.append(req.url) if 'embedded' in req.url else None)
        await page.reload(wait_until='networkidle')
        await page.wait_for_timeout(3000)

        # Get console logs
        print("\nConsole messages:")
        for msg in console_messages[:10]:  # Show first 10
            print(f"  {msg}")

        await browser.close()
        print(f"\n✓ Screenshot saved to: {screenshot_path}")
        print("Please check the screenshot for visual confirmation.")

if __name__ == "__main__":
    asyncio.run(check_embedded_dashboard())
