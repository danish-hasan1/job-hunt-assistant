import os, time, json
from datetime import date
from playwright.sync_api import sync_playwright
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_company_contact(company_name):
    contacts = []
    query = f"{company_name} talent acquisition HR recruiter"
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=400)
        page = browser.new_page()
        try:
            page.goto("https://www.linkedin.com/feed/", timeout=15000)
            time.sleep(2)
            if "login" in page.url or "authwall" in page.url:
                page.goto("https://www.linkedin.com/login", timeout=15000)
                page.wait_for_url("**/feed/**", timeout=60000)
            url = f"https://www.linkedin.com/search/results/people/?keywords={query.replace(' ', '%20')}"
            page.goto(url, timeout=15000)
            time.sleep(3)
            cards = page.locator(".entity-result__item").all()[:5]
            for card in cards:
                try:
                    name = (
                        card.locator(".entity-result__title-text")
                        .inner_text(timeout=2000)
                        .split("\n")[0]
                        .strip()
                    )
                    role = (
                        card.locator(".entity-result__primary-subtitle")
                        .inner_text(timeout=2000)
                        .strip()
                    )
                    link_loc = card.locator("a.app-aware-link").first
                    href = link_loc.get_attribute("href") if link_loc else None
                    if name and href:
                        contacts.append(
                            {
                                "name": name,
                                "role": role,
                                "url": href.split("?", 1)[0],
                                "company": company_name,
                            }
                        )
                except Exception:
                    continue
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()
    return contacts


def generate_outreach_message(contact_name, company_name, job_title, profile, groq_client):
    prompt = f"""Write a LinkedIn connection request from {profile.get('name')} to {contact_name} at {company_name}.
MAX 280 characters. Do NOT mention applying for a job.
Sound curious about company culture. Ask soft question about their experience.
No emojis. No "I am reaching out because". Human and warm.
Return ONLY the message."""
    try:
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return r.choices[0].message.content.strip()[:280]
    except Exception as e:
        return (
            f"Hi {contact_name.split()[0]}, I've been following {company_name} and would love to connect. "
            f"How has your experience been there?"
        )


def send_connection_request(profile_url, message):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=400)
        page = browser.new_page()
        try:
            page.goto("https://www.linkedin.com/feed/", timeout=15000)
            if "login" in page.url or "authwall" in page.url:
                page.goto("https://www.linkedin.com/login", timeout=15000)
                page.wait_for_url("**/feed/**", timeout=60000)
            page.goto(profile_url, timeout=15000)
            time.sleep(3)
            for sel in ["button:has-text('Connect')", "button[aria-label*='Connect']"]:
                try:
                    btn = page.locator(sel).first
                    if btn and btn.is_visible():
                        btn.click()
                        time.sleep(2)
                        break
                except Exception:
                    continue
            for sel in ["button:has-text('Add a note')", "button[aria-label*='note']"]:
                try:
                    btn = page.locator(sel).first
                    if btn and btn.is_visible():
                        btn.click()
                        time.sleep(1)
                        break
                except Exception:
                    continue
            try:
                field = page.locator("textarea[name='message']").first
                if field and field.is_visible():
                    field.fill(message)
                    time.sleep(1)
            except Exception:
                pass
            page.evaluate(
                "document.querySelectorAll('button').forEach(b=>{"
                "if(b.textContent.includes('Send')){"
                "b.style.border='4px solid #00ff00';"
                "b.style.backgroundColor='#00aa00';"
                "b.style.color='white';"
                "b.style.fontSize='18px';"
                "}})"
            )
            print("✅ Click the GREEN SEND button!")
            time.sleep(20)
            browser.close()
            return True, "Request sent"
        except Exception as e:
            browser.close()
            return False, str(e)


def save_outreach(job_id, company, name, role, url, message):
    import sqlite3

    conn = sqlite3.connect("data/jobs.db")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS outreach (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, company TEXT, contact_name TEXT, contact_role TEXT, contact_url TEXT, message TEXT, status TEXT DEFAULT 'sent', date_sent TEXT)"
    )
    conn.execute(
        "INSERT INTO outreach (job_id,company,contact_name,contact_role,contact_url,message,date_sent) VALUES (?,?,?,?,?,?,?)",
        (job_id, company, name, role, url, message, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Outreach agent ready ✓")
