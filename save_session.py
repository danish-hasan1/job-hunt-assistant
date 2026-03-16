from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.firefox.launch(
        headless=False,
        executable_path="/Applications/Firefox.app/Contents/MacOS/firefox"
    )
    context = browser.new_context()
    page = context.new_page()
    page.goto('https://www.linkedin.com/login')
    print('Log in with EMAIL and PASSWORD in Firefox window')
    input('Press ENTER after you see your LinkedIn feed: ')
    cookies = context.cookies()
    with open('linkedin_cookies.json', 'w') as f:
        json.dump(cookies, f)
    print(f'Saved {len(cookies)} cookies!')
    browser.close()
