import os
import time as _time
import json as _json
from datetime import date
from playwright.sync_api import sync_playwright
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_browser_with_session(p):
    browser = p.webkit.launch(headless=False, slow_mo=200)
    context = browser.new_context()
    try:
        cookies = _json.load(open('linkedin_cookies.json'))
        context.add_cookies(cookies)
        print(f'Loaded {len(cookies)} cookies')
    except Exception as e:
        print(f'Cookie error: {e}')
    page = context.new_page()
    return browser, context, page

def find_company_contact(company_name):
    contacts = []
    query = f"{company_name} talent acquisition recruitment HR director"
    
    with sync_playwright() as p:
        browser, context, page = get_browser_with_session(p)
        try:
            url = f"https://www.linkedin.com/search/results/people/?keywords={query.replace(' ','%20')}"
            page.goto(url, timeout=20000)
            _time.sleep(6)
            seen = set()
            links = page.locator('a[href*="/in/"]').all()
            print(f'Found {len(links)} profile links')
            for link in links[:20]:
                try:
                    href = link.get_attribute('href', timeout=2000)
                    if not href or '/in/' not in href:
                        continue
                    clean_url = href.split('?')[0]
                    if clean_url in seen:
                        continue
                    seen.add(clean_url)
                    text = link.inner_text(timeout=2000).strip()
                    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 2]
                    if not lines:
                        continue
                    name = lines[0]
                    for badge in ['• 1st','• 2nd','• 3rd','· 1st','· 2nd','· 3rd']:
                        name = name.replace(badge,'').strip()
                    if len(name) < 3 or len(name) > 60:
                        continue
                    role = lines[1][:100] if len(lines) > 1 else 'Recruitment Professional'
                    contacts.append({
                        'name': name,
                        'role': role,
                        'url': clean_url,
                        'company': company_name
                    })
                    print(f'  + {name} | {role}')
                    if len(contacts) >= 5:
                        break
                except:
                    continue
        except Exception as e:
            print(f'Error: {e}')
        finally:
            _time.sleep(2)
            browser.close()
    return contacts

def generate_outreach_message(contact_name, company_name, job_title, profile, groq_client):
    prompt = f"""Write a personalised LinkedIn connection request from {profile.get('name')} to {contact_name} at {company_name}.
MAX 280 characters.
Goals:
- Open a warm conversation about their work and the company
- Show one specific point of alignment with this role: {job_title}
- Sound like a senior recruitment/RPO leader, not a junior recruiter

Rules:
- Do NOT mention applying for a job or phrases like "role" or "position"
- No generic phrases like "I hope you are doing well" or "I am reaching out because"
- No emojis
- Use natural, concise language that feels human
- Ask one thoughtful question about their experience, team, or culture
- Return ONLY the message text, no quotes, no explanation"""
    try:
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return r.choices[0].message.content.strip()[:280]
    except Exception as e:
        return f"Hi {contact_name.split()[0]}, I've been following {company_name} and would love to connect. How has your experience been there?"

def send_connection_request(profile_url, message):
    with sync_playwright() as p:
        browser, context, page = get_browser_with_session(p)
        try:
            page.goto(profile_url, timeout=15000)
            _time.sleep(3)
            for sel in ["button:has-text('Connect')", "button[aria-label*='Connect']"]:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        _time.sleep(2)
                        break
                except:
                    continue
            for sel in ["button:has-text('Add a note')", "button[aria-label*='note']"]:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        _time.sleep(1)
                        break
                except:
                    continue
            try:
                field = page.locator("textarea[name='message']").first
                if field.is_visible(timeout=3000):
                    field.fill(message)
                    _time.sleep(1)
            except:
                pass
            page.evaluate("document.querySelectorAll('button').forEach(b=>{if(b.textContent.includes('Send')){b.style.border='4px solid #00ff00';b.style.backgroundColor='#00aa00';b.style.color='white';b.style.fontSize='18px';}})")
            print("Click the GREEN SEND button!")
            _time.sleep(20)
            browser.close()
            return True, "Request sent"
        except Exception as e:
            browser.close()
            return False, str(e)

def save_outreach(job_id, company, name, role, url, message):
    import sqlite3
    conn = sqlite3.connect("data/jobs.db")
    conn.execute("CREATE TABLE IF NOT EXISTS outreach (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, company TEXT, contact_name TEXT, contact_role TEXT, contact_url TEXT, message TEXT, status TEXT DEFAULT 'sent', date_sent TEXT)")
    conn.execute("INSERT INTO outreach (job_id,company,contact_name,contact_role,contact_url,message,date_sent) VALUES (?,?,?,?,?,?,?)", (job_id,company,name,role,url,message,date.today().isoformat()))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print("Outreach agent ready ✓")
    contacts = find_company_contact('Randstad')
    print('Contacts:', len(contacts))
    for c in contacts:
        print(c)
