import os, smtplib, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

GMAIL = os.getenv("GMAIL_ADDRESS")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")


def extract_email_from_jd(description):
    if not description:
        return None
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, description)
    # Filter out example/noreply emails
    valid = [e for e in emails if not any(x in e.lower() for x in ["example", "noreply", "no-reply", "test@"])]
    return valid[0] if valid else None


def find_company_email(company_name, groq_client):
    prompt = f"""Find the recruitment/HR email for {company_name}.
Return ONLY the email address, nothing else.
If unknown, return: unknown
Common patterns: careers@company.com, hr@company.com, recruitment@company.com"""
    try:
        r = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        result = r.choices[0].message.content.strip()
        if "@" in result and "unknown" not in result.lower():
            return result
        return None
    except:
        return None


def send_application_email(to_email, subject, body, cv_path, cl_path):
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        for file_path in [cv_path, cl_path]:
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(file_path)
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL, GMAIL_PASS)
            server.send_message(msg)
        print(f"✅ Email sent to {to_email}")
        return True, f"Email sent to {to_email}"
    except Exception as e:
        return False, f"Email error: {str(e)}"


def build_email_subject(job, profile):
    return f"Application: {job['title']} | {profile.get('name')} | {profile.get('years_experience')}+ Years Experience"


def build_email_body(job, profile, cover_letter):
    return f"""Dear Hiring Team,

{cover_letter}

Please find attached my tailored CV and cover letter for the {job['title']} position at {job['company']}.

Key highlights:
- {profile.get('current_portfolio', '')}
- 100% client retention across entire portfolio
- 125% productivity improvement via AI-enabled processes
- European, India, and Middle East market expertise

I am based in India and actively seeking relocation to Europe, with full flexibility on start date.

Best regards,
{profile.get('name')}
{profile.get('phone')}
{profile.get('email')}
LinkedIn: linkedin.com/in/danishhasan"""


if __name__ == "__main__":
    print("Email engine ready ✓")
