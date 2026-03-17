import sys, os, time, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.database import insert_job, init_db
from datetime import date
from playwright.sync_api import sync_playwright


def get_browser():
    p_instance = sync_playwright().start()
    browser = p_instance.webkit.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    )
    page = context.new_page()
    return p_instance, browser, page


def scrape_google_jobs(role, location, track="B", max_results=20):
    init_db()
    saved = 0
    query = f"{role} {location} jobs".replace(" ", "+")
    url = f"https://www.google.com/search?q={query}&ibp=htl;jobs"

    p_instance, browser, page = get_browser()
    try:
        page.goto(url, timeout=20000)
        time.sleep(4)

        job_cards = page.locator("li.iFjolb").all()
        if not job_cards:
            job_cards = page.locator("[data-ved]").all()

        print(f"  Found {len(job_cards)} potential cards")

        import re

        html = page.content()

        titles = re.findall(r'class="BjJfJf[^"]*"[^>]*>([^<]+)<', html)
        companies = re.findall(r'class="vNEEBe[^"]*"[^>]*>([^<]+)<', html)
        locations = re.findall(r'class="Qk80Jf[^"]*"[^>]*>([^<]+)<', html)

        if not titles:
            titles = re.findall(r'"jobTitle":"([^"]+)"', html)
            companies = re.findall(r'"companyName":"([^"]+)"', html)
            locations = re.findall(r'"location":"([^"]+)"', html)

        print(f"  Titles: {titles[:3]}")

        for i, title in enumerate(titles[:max_results]):
            company = companies[i] if i < len(companies) else "Unknown"
            loc = locations[i] if i < len(locations) else location
            desc_lower = (title + company).lower()
            sponsorship = (
                "possible"
                if any(k in desc_lower for k in ["visa", "sponsor", "relocat"])
                else "unknown"
            )
            job = {
                "title": title,
                "company": company,
                "location": loc,
                "track": track,
                "source": "google_jobs",
                "url": url,
                "description": f"{title} at {company} in {loc}",
                "salary": "Not disclosed",
                "sponsorship": sponsorship,
                "date_found": date.today().isoformat(),
            }
            insert_job(job)
            saved += 1
            print(f"  + [{track}] {title} | {company}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        browser.close()
        p_instance.stop()

    return saved


def scrape_multiple_queries(searches):
    total = 0
    for role, location, track in searches:
        print(f"Google Jobs: {role} in {location}")
        count = scrape_google_jobs(role, location, track)
        total += count
        time.sleep(3)
    print(f"Total: {total}")
    return total


if __name__ == "__main__":
    scrape_multiple_queries(
        [
            ("Head of Talent Acquisition", "Spain", "B"),
            ("RPO Delivery Manager", "Europe", "B"),
            ("EMEA Recruitment Manager", "India", "A"),
        ]
    )
