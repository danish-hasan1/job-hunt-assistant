import requests
from bs4 import BeautifulSoup
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.database import insert_job, init_db
from datetime import date
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

SEARCHES = [
    ("RPO delivery manager Europe", "India", "A"),
    ("EMEA talent acquisition manager", "India", "A"),
    ("global recruitment manager Europe", "India", "A"),
    ("associate director talent acquisition", "India", "A"),
    ("head of talent acquisition Europe", "India", "A"),
    ("associate director recruitment", "Europe", "B"),
    ("head of talent acquisition", "Spain", "B"),
    ("head of talent acquisition", "Belgium", "B"),
    ("RPO director", "United Kingdom", "B"),
    ("VP talent acquisition", "Netherlands", "B"),
    ("talent acquisition director", "France", "B"),
    ("recruitment director", "Germany", "B"),
]

SENIOR_KEYWORDS = [
    "director",
    "head",
    "vp",
    "vice president",
    "associate director",
    "senior manager",
    "manager",
    "lead",
    "principal",
    "rpo",
    "emea",
    "global",
]

REJECT_KEYWORDS = [
    "junior",
    "trainee",
    "intern",
    "graduate",
    "coordinator",
    "assistant",
    "executive recruiter",
    "sourcer",
    "resourcer",
]


def get_full_jd(job_url):
    try:
        r = requests.get(job_url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        desc = soup.find("div", class_="jobs-description__content")
        if not desc:
            desc = soup.find("div", class_="show-more-less-html__markup")
        if not desc:
            return ""
        text = desc.get_text(" ", strip=True)
        return text[:3000]
    except Exception:
        return ""


def scrape_jobs(keyword, location, track):
    jobs = []
    for start in [0, 25]:
        params = {
            "keywords": keyword,
            "location": location,
            "start": start,
            "sortBy": "DD",
        }
        try:
            r = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=15)
            if r.status_code != 200:
                print(f"  Status {r.status_code} for {keyword} in {location}")
                break
            soup = BeautifulSoup(r.text, "html.parser")
            cards = soup.find_all("div", class_="base-card")
            if not cards:
                break
            for card in cards:
                try:
                    title_tag = card.find("h3", class_="base-search-card__title")
                    company_tag = card.find("h4", class_="base-search-card__subtitle")
                    location_tag = card.find("span", class_="job-search-card__location")
                    link_tag = card.find("a", class_="base-card__full-link")

                    title = title_tag.text.strip() if title_tag else "N/A"
                    company = company_tag.text.strip() if company_tag else "Unknown"
                    loc = location_tag.text.strip() if location_tag else location
                    link = link_tag["href"].split("?")[0] if link_tag else ""

                    if title == "N/A" or not link:
                        continue
                    title_lower = title.lower()
                    if any(k in title_lower for k in REJECT_KEYWORDS):
                        continue
                    if not any(k in title_lower for k in SENIOR_KEYWORDS):
                        continue

                    full_desc = get_full_jd(link) if link else ""

                    desc_lower = (title + company).lower()
                    sponsorship = (
                        "possible"
                        if any(
                            k in desc_lower
                            for k in ["visa", "sponsor", "relocat", "relocation"]
                        )
                        else "unknown"
                    )

                    jobs.append(
                        {
                            "title": title,
                            "company": company,
                            "location": loc,
                            "track": track,
                            "source": "linkedin",
                            "url": link,
                            "description": full_desc if full_desc else f"{title} at {company} in {loc}. Search: {keyword}",
                            "salary": "Not disclosed",
                            "sponsorship": sponsorship,
                            "date_found": date.today().isoformat(),
                        }
                    )
                except:
                    continue
            time.sleep(2)
        except Exception as e:
            print(f"  Error: {e}")
            break
    return jobs


def scrape_linkedin():
    init_db()
    total = 0
    for keyword, location, track in SEARCHES:
        print(f"Searching: {keyword} in {location} [Track {track}]")
        jobs = scrape_jobs(keyword, location, track)
        for job in jobs:
            insert_job(job)
            total += 1
            print(
                f"  + [{job['track']}] {job['title']} | {job['company']} | {job['location']}"
            )
        time.sleep(3)
    print(f"\nTotal LinkedIn jobs saved: {total}")
    return total


if __name__ == "__main__":
    print("Starting LinkedIn scraper...")
    scrape_linkedin()
