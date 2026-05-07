from playwright.sync_api import sync_playwright

print("STARTING TEST...")

with sync_playwright() as p:
    print("Playwright initialized")

    browser = p.chromium.launch(headless=False)
    print("Browser launched")

    page = browser.new_page()
    page.goto("https://www.google.com")

    print("Page opened")

    page.wait_for_timeout(5000)

    browser.close()

print("DONE")