import requests
from bs4 import BeautifulSoup
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.database import insert_job, init_db
from datetime import date
import time

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

SEARCHES = [
    (" `https://in.indeed.com/rss?q=european+recruitment+manager&l=India&sort=date` ", "A"),
    (" `https://in.indeed.com/rss?q=EMEA+talent+acquisition&l=India&sort=date` ", "A"),
    (" `https://in.indeed.com/rss?q=RPO+delivery+manager&l=India&sort=date` ", "A"),
    (" `https://in.indeed.com/rss?q=associate+director+recruitment&l=India&sort=date` ", "A"),
    (" `https://www.indeed.co.uk/rss?q=head+of+talent+acquisition&sort=date` ", "B"),
    (" `https://www.indeed.co.uk/rss?q=RPO+director&sort=date` ", "B"),
    (" `https://es.indeed.com/rss?q=talent+acquisition+director&sort=date` ", "B"),
    (" `https://www.indeed.com/rss?q=VP+talent+acquisition+Europe&sort=date` ", "B"),
]

def scrape_indeed():
    init_db()
    total = 0
    for url, track in SEARCHES:
        keyword = url.split('q=')[1].split('&')[0].replace('+', ' ')
        print(f"Searching: {keyword}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.content, 'xml')
            items = soup.find_all('item')
            if not items:
                soup = BeautifulSoup(r.content, 'html.parser')
                items = soup.find_all('item')
            for item in items:
                try:
                    title = item.find('title').text.strip() if item.find('title') else 'N/A'
                    link = item.find('link').text.strip() if item.find('link') else ''
                    desc_raw = item.find('description').text.strip() if item.find('description') else ''
                    company_tag = item.find('source')
                    company = company_tag.text.strip() if company_tag else 'Unknown'
                    clean_desc = BeautifulSoup(desc_raw, 'html.parser').get_text(separator=' ').strip()
                    desc_lower = (title + clean_desc).lower()
                    sponsorship = 'possible' if any(k in desc_lower for k in ['visa','sponsor','relocat']) else 'unknown'
                    if any(k in title.lower() for k in ['junior','trainee','intern','graduate']):
                        continue
                    insert_job({
                        'title': title, 'company': company, 'location': 'Not specified',
                        'track': track, 'source': 'indeed', 'url': link,
                        'description': clean_desc[:2000], 'salary': 'Not disclosed',
                        'sponsorship': sponsorship, 'date_found': date.today().isoformat()
                    })
                    total += 1
                    print(f"  ✓ [{track}] {title} | {company}")
                except:
                    continue
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(2)
    print(f"\nTotal saved: {total}")
    return total

if __name__ == "__main__":
    scrape_indeed()

