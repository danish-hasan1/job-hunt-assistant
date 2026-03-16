import os
import sys
import time
from datetime import date

import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from engines.database import init_db, insert_job


BASE_URL = "https://www.naukri.com/jobapi/v3/search"

KEYWORDS = [
    "european recruitment manager",
    "EMEA talent acquisition",
    "RPO delivery manager",
    "associate director recruitment",
    "head of talent acquisition",
    "global recruitment manager",
]

TRACK_A_TERMS = [
    "europe",
    "emea",
    "european",
    "rpo",
    "msp",
    "global delivery",
]

SPONSORSHIP_TERMS = [
    "visa",
    "sponsorship",
    "relocation",
]


def build_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "appid": "109",
        "systemid": "Naukri",
        "Accept": "application/json",
        "Referer": "https://www.naukri.com/",
        "Origin": "https://www.naukri.com",
    }


def extract_placeholder(job, placeholder_type):
    placeholders = job.get("placeholders") or []
    values = [
        p.get("label")
        for p in placeholders
        if isinstance(p, dict) and p.get("type") == placeholder_type and p.get("label")
    ]
    return ", ".join(values)


def classify_track(description):
    text = (description or "").lower()
    for term in TRACK_A_TERMS:
        if term in text:
            return "A"
    return "B"


def detect_sponsorship(description):
    text = (description or "").lower()
    for term in SPONSORSHIP_TERMS:
        if term in text:
            return True
    return False


def fetch_page(keyword, page):
    params = {
        "noOfResults": 20,
        "urlType": "search_by_key_loc",
        "searchType": "adv",
        "keyword": keyword,
        "pageNo": page,
        "k": keyword,
        "l": "",
        "experience": 5,
        "jobAge": 7,
    }
    response = requests.get(BASE_URL, headers=build_headers(), params=params, timeout=15)
    if response.status_code != 200:
        return []
    try:
        data = response.json()
    except ValueError:
        return []
    return data.get("jobDetails") or []


def scrape_naukri():
    init_db()
    total_found = 0
    total_saved = 0

    for keyword in KEYWORDS:
        page = 1
        while True:
            jobs = fetch_page(keyword, page)
            if not jobs:
                break

            for job in jobs:
                title = job.get("title") or ""
                company = job.get("companyName") or ""
                location = extract_placeholder(job, "location")
                salary = extract_placeholder(job, "salary")
                raw_description = job.get("jobDescription") or ""
                description = BeautifulSoup(raw_description, "html.parser").get_text(
                    separator=" ", strip=True
                )
                url = job.get("jdURL") or ""
                job_id = job.get("jobId")

                track = classify_track(description)
                sponsorship_flag = detect_sponsorship(description)

                job_record = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "track": track,
                    "source": "Naukri",
                    "url": url,
                    "description": description,
                    "salary": salary,
                    "sponsorship": "yes" if sponsorship_flag else "no",
                    "date_found": date.today().isoformat(),
                }

                insert_job(job_record)

                total_found += 1
                total_saved += 1

                print(f"{title} | {company} | {location} | Track {track}")

            page += 1
            time.sleep(2)

    print(f"Total jobs found: {total_found}")
    print(f"Total jobs saved to database: {total_saved}")


if __name__ == "__main__":
    scrape_naukri()
