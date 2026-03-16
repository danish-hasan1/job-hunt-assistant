import os
import json
import google.genai as genai
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.0-flash-lite"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def load_cv_notes():
    try:
        with open("profile.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}


def score_job(job_description, profile):
    cv_notes = load_cv_notes()
    search_keywords = cv_notes.get("job_search_strategy", {}).get("search_keywords", [])
    preferred_industries = cv_notes.get("preferred_industries", [])

    prompt = f"""You are an expert recruitment consultant. Score this job against the candidate profile.

CANDIDATE PROFILE:
- Name: {profile.get('name')}
- Current Title: {profile.get('current_title')}
- Target roles: {profile.get('target_roles')}
- Experience markets: {profile.get('experience_markets')}
- Key achievements: {profile.get('key_achievements')}
- Skills: {profile.get('skills')}
- Preferred industries: {preferred_industries}
- Search keywords: {search_keywords}
- Relocate: {profile.get('relocate')}
- India EU roles open: {profile.get('india_eu_roles')}

JOB DESCRIPTION:
{job_description[:2000]}

Scoring: 90-100 perfect match, 70-89 strong, 50-69 partial, below 50 poor.

Return ONLY valid JSON, no markdown, no backticks:
{{"score": <0-100>, "reason": "<one sentence>", "sponsorship_likely": <true/false>, "track_fit": "<A or B or both>", "seniority_match": <true/false>}}"""

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            print(f"Groq failed, trying Gemini: {e}")

    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        return {
            "score": 0,
            "reason": f"Scoring error: {str(e)}",
            "sponsorship_likely": False,
            "track_fit": "unknown",
            "seniority_match": False,
        }

def tailor_cv(master_cv_text, job_description, profile):
    cv_notes = load_cv_notes()
    industries = cv_notes.get("industries", [])
    value_props = cv_notes.get("career_summary", {}).get("value_proposition", [])

    prompt = f"""You are an expert CV writer for senior recruitment and HR leadership roles.
Rewrite the professional summary for this candidate targeting this specific job.

CANDIDATE:
- Name: {profile.get('name')}
- Current Title: {profile.get('current_title')}
- Years Experience: {profile.get('years_experience')}
- Current Portfolio: {profile.get('current_portfolio')}
- Experience Markets: {profile.get('experience_markets')}
- Key Achievements: {profile.get('key_achievements')}
- Industries: {industries}
- Value Propositions: {value_props}

CURRENT SUMMARY:
{master_cv_text}

JOB DESCRIPTION:
{job_description[:1500]}

Rules:
- 4-5 sentences only
- Mirror keywords from JD naturally
- Include at least one metric (€5M portfolio, 135 consultants, 100% retention)
- End with confident relocation/availability statement
- No phrases like results-driven or passionate about
- Return ONLY the paragraph, nothing else"""

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Groq tailoring error: {str(e)}"
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"CV tailoring error: {str(e)}"


def generate_cover_letter(company, role, job_description, profile):
    prompt = f"""Write a professional cover letter for this job application.

CANDIDATE: {profile.get('name')}, based in India
TARGET ROLE: {role} at {company}
EXPERIENCE: {profile.get('experience_markets')}
ACHIEVEMENTS: {profile.get('key_achievements')}
CURRENT PORTFOLIO: {profile.get('current_portfolio')}

JOB DESCRIPTION:
{job_description[:1500]}

Write exactly 3 paragraphs:
1. Why this company and role — reference something specific
2. Why the candidate fits — use real metrics and European/global experience
3. Relocation commitment and confident close

Rules:
- No "I am writing to apply" openings
- No generic phrases
- Professional but warm tone
- Return only the letter text"""

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Groq cover letter error: {str(e)}"
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"Cover letter error: {str(e)}"

def generate_interview_prep(company, role, job_description, cv_text, profile):
    prompt = f"""Create an interview preparation pack for this candidate.

CANDIDATE: {profile.get('name')}
CURRENT TITLE: {profile.get('current_title')}
ROLE APPLYING FOR: {role} at {company}
EXPERIENCE MARKETS: {profile.get('experience_markets')}
KEY ACHIEVEMENTS: {profile.get('key_achievements')}

JOB DESCRIPTION:
{job_description[:1500]}

Return ONLY a valid JSON object, no markdown, no backticks, no explanation:
{{"company_brief": "<3 sentences about the company and role>", "key_themes": ["<theme1>", "<theme2>", "<theme3>"], "questions": [{{"question": "<question>", "suggested_answer": "<answer using candidate background>"}}, {{"question": "<question>", "suggested_answer": "<answer>"}}, {{"question": "<question>", "suggested_answer": "<answer>"}}, {{"question": "<question>", "suggested_answer": "<answer>"}}, {{"question": "<question>", "suggested_answer": "<answer>"}}], "questions_to_ask": ["<smart question to ask interviewer>", "<another smart question>", "<third smart question>"], "red_flags_to_address": ["<potential concern and how to handle it>"]}}"""

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text.strip())
        except Exception as e:
            return {"error": f"Groq interview prep error: {str(e)}"}

    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("Gemini engine ready ✓")
