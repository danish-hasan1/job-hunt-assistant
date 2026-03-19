import sys, os, requests, time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.database import insert_job, init_db
from datetime import date
from dotenv import load_dotenv
load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

DEFAULT_SEARCHES = [
    ("talent acquisition manager EMEA India", "A"),
    ("RPO delivery manager India Europe clients", "A"),
    ("global recruitment manager India EMEA", "A"),
    ("head of talent acquisition Europe relocation", "B"),
    ("associate director talent acquisition Europe", "B"),
    ("recruitment director Spain Belgium France", "B"),
    ("VP talent acquisition Europe", "B"),
    ("talent acquisition lead pharma Europe", "B"),
]

def scrape_google_jobs(query, track="B", max_results=10):
    init_db()
    if not SERPAPI_KEY:
        print("No SERPAPI_KEY in .env")
        return 0

    params = {
        "engine": "google_jobs",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "gl": "us",
        "num": max_results
    }

    try:
        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        data = r.json()
        jobs_results = data.get("jobs_results", [])
        print(f"  Found {len(jobs_results)} jobs")

        saved = 0
        for job in jobs_results:
            title = job.get('title', '')
            if any(k in title.lower() for k in ['junior','intern','trainee','graduate','coordinator','sourcer']):
                continue
            us_only = ['NY', 'NJ', 'CA', 'TX', 'IL', 'PA', 'MD', 'KS', 'DE', 'NC', 'MA', 'VA', 'GA', 'FL', 'OH']
            location = job.get('location', '')
            if any(f', {s}' in location for s in us_only) and 'India' not in location and 'Europe' not in location:
                continue
            desc = job.get('description', '')
            desc_lower = desc.lower()
            sponsorship = 'possible' if any(k in desc_lower for k in ['visa','sponsor','relocat']) else 'unknown'
            extensions = job.get('detected_extensions', {})
            salary = extensions.get('salary', 'Not disclosed')
            insert_job({
                'title': title,
                'company': job.get('company_name', 'Unknown'),
                'location': job.get('location', ''),
                'track': track,
                'source': f"google_{job.get('via','jobs').replace(' ','_')[:15]}",
                'url': job.get('share_link', ''),
                'description': desc[:2000],
                'salary': salary,
                'sponsorship': sponsorship,
                'date_found': date.today().isoformat()
            })
            saved += 1
            print(f"  + [{track}] {title} | {job.get('company_name')} | {job.get('location')}")
        return saved
    except Exception as e:
        print(f"Error: {e}")
        return 0

def scrape_all_google_jobs():
    total = 0
    for query, track in DEFAULT_SEARCHES:
        print(f"Searching: {query}")
        count = scrape_google_jobs(query, track)
        total += count
        time.sleep(1)
    print(f"\nTotal saved: {total}")
    return total

def scrape_custom_google_jobs(role, location, track, extra_keywords=None):
    total = 0
    queries = [f"{role} {location}"]
    if extra_keywords:
        for kw in extra_keywords[:2]:
            queries.append(f"{role} {kw} {location}")
    for q in queries:
        print(f"Google Jobs: {q}")
        count = scrape_google_jobs(q, track)
        total += count
        time.sleep(1)
    return total

if __name__ == "__main__":
    scrape_all_google_jobs()
