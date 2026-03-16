import os, time, subprocess
from datetime import date
from playwright.sync_api import sync_playwright
import json as _json


def get_browser_with_session(p):
    import json as _json
    browser = p.webkit.launch(headless=False, slow_mo=400)
    context = browser.new_context()
    try:
        cookies = _json.load(open("linkedin_cookies.json"))
        context.add_cookies(cookies)
    except:
        pass
    page = context.new_page()
    return browser, context, page


def apply_linkedin_semi_auto(job, cv_path, profile):
    job_url = job.get("url", "")
    if not job_url:
        return False, "No job URL found"
    if "?" in job_url:
        job_url = job_url.split("?", 1)[0]
    print(f"Opening: {job['title']} at {job['company']}")
    with sync_playwright() as p:
        browser, context, page = get_browser_with_session(p)
        try:
            page.goto(job_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            easy_apply_btn = None
            for sel in [
                "button[aria-label*='Easy Apply']",
                "button.jobs-apply-button",
                "button:has-text('Easy Apply')",
            ]:
                try:
                    btn = page.locator(sel).first
                    if btn and btn.is_visible():
                        easy_apply_btn = btn
                        break
                except Exception:
                    continue
            if not easy_apply_btn:
                subprocess.run(["open", job_url])
                browser.close()
                return False, "Not Easy Apply - opened in browser"
            easy_apply_btn.click()
            time.sleep(2)
            try:
                phone = page.locator("input[id*='phoneNumber']").first
                if phone and phone.is_visible():
                    phone.fill(profile.get("phone", ""))
            except Exception:
                pass
            if cv_path and os.path.exists(cv_path):
                try:
                    fi = page.locator("input[type='file']").first
                    if fi and fi.is_visible():
                        fi.set_input_files(os.path.abspath(cv_path))
                        print("✓ CV uploaded")
                        time.sleep(2)
                except Exception:
                    print("Could not auto-upload CV")
            for step in range(8):
                time.sleep(1)
                submit_btn = None
                for sel in [
                    "button[aria-label='Submit application']",
                    "button:has-text('Submit application')",
                    "button:has-text('Submit')",
                ]:
                    try:
                        btn = page.locator(sel).first
                        if btn and btn.is_visible():
                            submit_btn = btn
                            break
                    except Exception:
                        continue
                if submit_btn:
                    page.evaluate(
                        "document.querySelectorAll('button').forEach(b => { "
                        "if(b.textContent.includes('Submit')){"
                        "b.style.border='4px solid #00ff00';"
                        "b.style.backgroundColor='#00aa00';"
                        "b.style.color='white';"
                        "b.style.fontSize='20px';"
                        "}})"
                    )
                    print(
                        "\n✅ READY! Confirm everything, then click the GREEN SUBMIT button in the browser window!"
                    )
                    return True, "Ready for manual submit"
                next_clicked = False
                for sel in [
                    "button[aria-label='Continue to next step']",
                    "button:has-text('Next')",
                    "button:has-text('Review')",
                ]:
                    try:
                        btn = page.locator(sel).first
                        if btn and btn.is_visible():
                            btn.click()
                            next_clicked = True
                            print(f"  Step {step+1} done")
                            break
                    except Exception:
                        continue
                if not next_clicked:
                    break
            browser.close()
            return False, "Could not complete flow"
        except Exception as e:
            browser.close()
            return False, f"Error: {str(e)}"


def launch_apply(job_dict, cv_path, profile_dict):
    import subprocess
    import json
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"job": job_dict, "cv_path": cv_path, "profile": profile_dict}, f)
        temp_path = f.name

    subprocess.Popen(
        [
            "python3",
            "-c",
            f'''
import json
from engines.apply_agent import apply_linkedin_semi_auto
data = json.load(open("{temp_path}"))
success, msg = apply_linkedin_semi_auto(data["job"], data["cv_path"], data["profile"])
print("Result:", success, msg)
''',
        ]
    )
    return True, "Browser launching..."


if __name__ == "__main__":
    print("Apply agent ready ✓")
