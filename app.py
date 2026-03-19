import streamlit as st 
import pandas as pd 
import json 
import os 
from engines.database import init_db, get_all_jobs, get_stats, update_job_status, update_job_score, insert_hiring_targets, get_hiring_targets_by_status, update_hiring_target_status, update_hiring_target_message_flag 
from datetime import datetime, date 
 
st.set_page_config(page_title="Job Hunt Assistant", page_icon="🎯", layout="wide") 


def render_job_body(job):
    status_emoji = {'new': '🔵', 'approved': '🟢', 'rejected': '🔴', 'applied': '✅', 'interview': '🎤'}.get(job['status'], '🔵')
    if job['score'] >= 80:
        match_label = "🔥 High match"
    elif job['score'] >= 60:
        match_label = "👍 Good match"
    elif job['score'] > 0:
        match_label = "👌 Light match"
    else:
        match_label = "No score yet"
    source_raw = str(job.get('source') or '')
    src_lower = source_raw.lower()
    if 'linkedin' in src_lower:
        source_label = "LinkedIn"
    elif 'google' in src_lower:
        source_label = "Google Jobs"
    elif source_raw:
        source_label = source_raw
    else:
        source_label = "Unknown"
    header_text = f"{status_emoji} {job['title']} — {job['company']} | {match_label} ({job['score']}) | Src: {source_label} | Track {job['track']} | {job['status'].upper()}"
    with st.expander(header_text):
        col_a,col_b,col_c = st.columns(3)
        with col_a:
            st.markdown(f"**Company:** {job['company']}")
            st.markdown(f"**Location:** {job['location']}")
        with col_b:
            st.markdown(f"**Track:** {'🇮🇳 India-Based' if job['track']=='A' else '🇪🇺 Europe Direct'}")
            st.markdown(
                f"**Sponsorship:** {'🟢 Yes' if str(job['sponsorship']).lower().startswith('y') else '⚪️ No'}"
            )
        with col_c:
            st.markdown(f"**Score:** {job['score']}")
            st.markdown(
                f"**Source:** {'🌐 LinkedIn' if str(job['source']).lower()=='linkedin' else str(job['source'])}"
            )
        if job['description']:
            st.markdown(f"**Description:** {job['description'][:300]}...")
        if job['url']:
            st.markdown(f"[🔗 View Job]({job['url']})")
        cx, cy, cz, cw, c5 = st.columns(5)
        with cx:
            if st.button("✅ Approve", key=f"ap_{job['id']}"):
                update_job_status(job['id'], 'approved')
                st.rerun()
        with cy:
            if st.button("❌ Reject", key=f"rj_{job['id']}"):
                update_job_status(job['id'], 'rejected')
                st.rerun()
        with cz:
            if st.button("📋 Applied", key=f"done_{job['id']}"):
                update_job_status(job['id'], 'applied')
                st.rerun()
        with cw:
            if st.button("📄 Generate CV", key=f"cv_{job['id']}"):
                with st.spinner(f"Generating CV..."):
                    from engines.cv_engine import generate_application_package
                    import engines.gemini_engine as gemini_engine
                    profile = json.load(open('profile.json'))
                    cv_path, cl_path, folder, error = generate_application_package(job, profile, gemini_engine)
                    if error:
                        st.error(f"Error: {error}")
                    else:
                        update_job_status(job['id'], 'approved')
                        st.success(f"✅ CV ready!")
                        st.markdown(f"📁 `{folder}`")
        with c5:
            if st.button("🚀 Auto Apply", key=f"auto_{job['id']}"):
                if not job.get("url"):
                    st.warning("⚠️ This job has no LinkedIn URL saved.")
                else:
                    profile = json.load(open("profile.json"))
                    from engines.cv_engine import generate_application_package
                    import engines.gemini_engine as gemini_engine
                    with st.spinner("Preparing tailored CV and cover letter..."):
                        cv_path, cl_path, folder, error = generate_application_package(
                            job, profile, gemini_engine
                        )
                    if error or not cv_path:
                        st.error(f"Error preparing CV: {error or 'no CV generated'}")
                    else:
                        st.success(f"✅ Application package ready: {folder}")
                        st.info("🌐 Opening LinkedIn... Click the GREEN submit button!")
                        from engines.apply_agent import launch_apply
                        success, message = launch_apply(dict(job), cv_path, profile)
                        if success:
                            st.success("✅ Browser opening... Check your screen!")
                            update_job_status(job["id"], "applied")
                        else:
                            st.warning(f"ℹ️ {message}")
        st.markdown("---")
        action_left, action_right = st.columns(2)
        with action_left:
            st.markdown("**📧 Email Application**")
            if st.button("🔍 Find Email", key=f"femail_{job['id']}"):
                from engines.email_engine import extract_email_from_jd, find_company_email
                from groq import Groq
                groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                email = extract_email_from_jd(job['description'])
                if not email:
                    with st.spinner("Searching for company email..."):
                        email = find_company_email(job['company'], groq_client)
                if email:
                    st.session_state[f"email_{job['id']}"] = email
                    st.success(f"📧 Found: {email}")
                else:
                    st.session_state[f"email_{job['id']}"] = ""
                    st.warning("No email found — enter manually")
        with action_right:
            st.markdown("**🤝 LinkedIn Outreach**")
            if st.button("🔍 Find Contact", key=f"find_{job['id']}"):
                with st.spinner("Searching LinkedIn..."):
                    try:
                        from engines.outreach_agent import find_company_contact
                        contacts = find_company_contact(job.get('company') or "")
                        if contacts:
                            st.session_state[f"contacts_{job['id']}"] = contacts
                            st.success(f"Found {len(contacts)} contact(s)!")
                        else:
                            st.warning("No contacts found")
                    except Exception as e:
                        st.error(f"Error searching LinkedIn contacts: {e}")
        if f"email_{job['id']}" in st.session_state:
            to_email = st.text_input("Recipient email:", value=st.session_state[f"email_{job['id']}"], key=f"emailinput_{job['id']}")
            if st.button("📧 Send Application", key=f"sendemail_{job['id']}"):
                safe_company = job['company'].replace(' ','_')[:30]
                safe_role = job['title'].replace(' ','_')[:25]
                folder = f"applications/{safe_company}_{safe_role}_{date.today().strftime('%d%b%Y')}"
                cv_files = [f for f in os.listdir(folder) if f.endswith('.pdf') and 'CV_' in f] if os.path.exists(folder) else []
                cl_files = [f for f in os.listdir(folder) if f.endswith('.pdf') and 'Cover' in f] if os.path.exists(folder) else []
                if not cv_files:
                    st.warning("⚠️ Generate CV first!")
                else:
                    cv_path = f"{folder}/{cv_files[0]}"
                    cl_path = f"{folder}/{cl_files[0]}" if cl_files else None
                    from engines.email_engine import send_application_email, build_email_subject, build_email_body
                    from engines.gemini_engine import generate_cover_letter
                    profile = json.load(open('profile.json'))
                    with st.spinner("Sending email..."):
                        cl_text = generate_cover_letter(job['company'], job['title'], job['description'], profile)
                        subject = build_email_subject(job, profile)
                        body = build_email_body(job, profile, cl_text)
                        success, message = send_application_email(to_email, subject, body, cv_path, cl_path)
                        if success:
                            update_job_status(job['id'], 'applied')
                            st.success(f"✅ Application sent to {to_email}!")
                        else:
                            st.error(f"❌ {message}")
        if f"contacts_{job['id']}" in st.session_state:
            contacts = st.session_state[f"contacts_{job['id']}"]
            labels = [f"{c['name']} — {c['role']}" for c in contacts]
            sel = st.selectbox("Select contact:", labels, key=f"sel_{job['id']}")
            contact = contacts[labels.index(sel)]
            st.markdown(f"**Selected contact:** {contact['name']} — {contact['role']}")
            st.caption(contact['company'])
            st.markdown(f"[Open LinkedIn profile]({contact['url']})")
            if st.button("✍️ Generate Message", key=f"genmsg_{job['id']}"):
                from engines.outreach_agent import generate_outreach_message
                from groq import Groq
                from dotenv import load_dotenv
                load_dotenv()
                groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                profile = json.load(open('profile.json'))
                msg = generate_outreach_message(contact['name'], job['company'], job['title'], profile, groq_client)
                st.session_state[f"msg_{job['id']}"] = msg
            if f"msg_{job['id']}" in st.session_state:
                edited = st.text_area("Review and edit your message (max 280):", value=st.session_state[f"msg_{job['id']}"], max_chars=280, key=f"edit_{job['id']}")
                st.caption(f"{len(edited)}/280 characters")
                if st.button("🚀 Send Request", key=f"send_{job['id']}"):
                    from engines.outreach_agent import save_outreach
                    import subprocess, tempfile, json as jmod
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        jmod.dump({'url': contact['url'], 'message': edited}, f)
                        tmp = f.name
                    subprocess.Popen(['python3', '-c', f'import json; from engines.outreach_agent import send_connection_request; d=json.load(open("{tmp}")); send_connection_request(d["url"],d["message"])'])
                    save_outreach(job['id'], job['company'], contact['name'], contact['role'], contact['url'], edited)
                    st.success(f"✅ Browser opening to connect with {contact['name']}!")

st.markdown("""<style> 
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Base Styles & Minimalist Background */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 0% 0%, rgba(191, 219, 254, 0.8) 0, transparent 55%),
                radial-gradient(circle at 100% 100%, rgba(224, 242, 254, 0.9) 0, transparent 60%),
                #F9FAFB;
    color: #0F172A;
}

/* Sidebar Styling - Clean Panel */
[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E5E7EB !important;
}
[data-testid="stSidebar"] * { color: #475569 !important; }
[data-testid="stSidebarNav"] { padding-top: 2rem; }

/* Header / Top Nav */
[data-testid="stHeader"] { background-color: transparent !important; }

/* Global Typography & Legibility */
h1 {
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    color: #0F172A !important;
    letter-spacing: -0.05em;
    margin-bottom: 24px !important;
}
h2, h3 { font-weight: 600 !important; color: #111827 !important; letter-spacing: -0.02em; }
p, label, li { color: #4B5563 !important; line-height: 1.6; font-size: 0.95rem; }
strong { color: #0F172A !important; font-weight: 600; }

/* Metric Cards - Sharp Vercel-like Aesthetic */
.metric-card {
    background: linear-gradient(145deg, #FFFFFF, #E0F2FE);
    border: 1px solid rgba(148, 163, 184, 0.35);
    border-radius: 18px;
    padding: 24px;
    text-align: center;
    transition: all 0.2s ease;
    margin-bottom: 18px;
    box-shadow:
        14px 14px 32px rgba(148, 163, 184, 0.45),
        -10px -10px 24px rgba(255, 255, 255, 0.95),
        inset 0 0 0 1px rgba(248, 250, 252, 0.9);
}

.metric-card:hover {
    border-color: rgba(37, 99, 235, 0.9);
    transform: translateY(-2px);
    box-shadow:
        18px 20px 40px rgba(148, 163, 184, 0.6),
        -12px -12px 28px rgba(255, 255, 255, 1),
        inset 0 0 0 1px rgba(219, 234, 254, 1);
}

.metric-value {
    font-size: 3rem;
    font-weight: 700;
    color: #0F172A;
    letter-spacing: -0.05em;
    line-height: 1;
}

.metric-label {
    font-size: 0.85rem;
    font-weight: 500;
    color: #64748B;
    margin-top: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.job-card {
    background: linear-gradient(145deg, #FFFFFF, #E0F2FE);
    border: 1px solid rgba(148, 163, 184, 0.4);
    border-radius: 18px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow:
        12px 14px 30px rgba(148, 163, 184, 0.45),
        -10px -10px 24px rgba(255, 255, 255, 0.98),
        inset 0 0 0 1px rgba(248, 250, 252, 0.9);
    cursor: pointer;
}

.job-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}

.job-card-title {
    font-weight: 600;
    color: #0F172A;
}

.job-card-score {
    font-weight: 600;
    color: #1D4ED8;
}

.job-card-company {
    font-size: 0.9rem;
    color: #475569;
    margin-bottom: 4px;
}

.job-card-meta {
    font-size: 0.8rem;
    color: #6B7280;
}

.job-card-tag {
    margin-top: 6px;
    font-size: 0.8rem;
    font-weight: 500;
    color: #1D4ED8;
}

/* Minimalist Primary Buttons */
.stButton>button {
    background: linear-gradient(135deg, #BFDBFE, #60A5FA);
    color: #0F172A !important;
    border: 1px solid rgba(148, 163, 184, 0.6);
    border-radius: 999px;
    font-weight: 600;
    padding: 0.75rem 1.5rem;
    font-size: 0.9rem;
    transition: all 0.18s ease-out;
    width: 100%;
    box-shadow:
        10px 12px 26px rgba(148, 163, 184, 0.55),
        -8px -8px 22px rgba(255, 255, 255, 0.95),
        inset 0 0 0 1px rgba(248, 250, 252, 0.7);
}

.stButton>button:hover {
    transform: translateY(-2px) scale(1.01);
    box-shadow:
        14px 16px 34px rgba(148, 163, 184, 0.7),
        -10px -10px 26px rgba(255, 255, 255, 1),
        inset 0 0 0 1px rgba(219, 234, 254, 1);
}

.stButton>button:active { 
    transform: translateY(0) scale(0.99);
    background: linear-gradient(135deg, #93C5FD, #3B82F6);
}

/* Secondary Actions / Expanders */
[data-testid="stExpander"] {
    background: linear-gradient(145deg, #FFFFFF, #E0F2FE) !important;
    border: 1px solid rgba(148, 163, 184, 0.4) !important;
    border-radius: 18px !important;
    overflow: hidden !important;
    margin-bottom: 1rem;
    transition: all 0.2s ease;
    box-shadow:
        12px 14px 30px rgba(148, 163, 184, 0.5),
        -10px -10px 24px rgba(255, 255, 255, 0.98),
        inset 0 0 0 1px rgba(248, 250, 252, 0.9);
}
[data-testid="stExpander"]:hover {
    border-color: rgba(37, 99, 235, 0.9) !important;
}
[data-testid="stExpander"] summary {
    padding: 1rem !important;
    font-size: 1rem;
    font-weight: 500;
    color: #0F172A !important;
}

/* Minimal Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94A3B8; }

/* DataFrame Styling - Clean Lines, High Contrast Borders */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(148, 163, 184, 0.4);
    border-radius: 18px;
    background: linear-gradient(145deg, #FFFFFF, #E5F0FF);
    box-shadow:
        14px 16px 34px rgba(148, 163, 184, 0.5),
        -10px -10px 24px rgba(255, 255, 255, 0.98),
        inset 0 0 0 1px rgba(248, 250, 252, 0.95);
}
[data-testid="stDataFrame"] table {
    width: 100% !important;
}

/* Clean Divider */
hr { 
    border: none !important; 
    border-top: 1px solid #E5E7EB !important;
    margin: 2rem 0 !important; 
}

/* Input Fields & Dropdowns - Sharp and Clean */
input, select, textarea {
    background: linear-gradient(145deg, #FFFFFF, #E5F0FF) !important;
    border: 1px solid rgba(148, 163, 184, 0.55) !important;
    border-radius: 16px !important;
    padding: 10px 14px !important;
    color: #0F172A !important;
    font-size: 0.95rem !important;
    font-weight: 400 !important;
    width: 100% !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
    box-shadow:
        10px 12px 26px rgba(148, 163, 184, 0.5),
        -8px -8px 22px rgba(255, 255, 255, 0.98),
        inset 0 0 0 1px rgba(248, 250, 252, 0.95);
}
input:focus, select:focus, textarea:focus {
    outline: none !important;
    border-color: rgba(37, 99, 235, 0.9) !important;
    box-shadow:
        14px 16px 34px rgba(148, 163, 184, 0.65),
        -10px -10px 26px rgba(255, 255, 255, 1),
        inset 0 0 0 1px rgba(219, 234, 254, 1) !important;
    transform: translateY(-1px);
}
</style>""", unsafe_allow_html=True) 
 
init_db() 
page = st.sidebar.radio(
    "🎯 Job Hunt Assistant",
    ["🏠 Home","💼 Jobs","📋 Applications","📁 CV Vault","🎤 Interview Prep","📣 Outreach","⚙️ Settings"],
) 


if page == "🏠 Home": 
    st.title("Welcome back, Danish! 👋") 
    st.caption(f"Today is {datetime.now().strftime('%A, %d %B %Y')}") 
    if "show_custom_search" not in st.session_state: 
        st.session_state["show_custom_search"] = False 
    st.markdown("---") 
    st.subheader("🔍 Job Search") 
    top_cs_col, _ = st.columns([1, 3]) 
    with top_cs_col: 
        if st.button("🔍 Custom Search", key="custom_search_toggle"): 
            st.session_state["show_custom_search"] = not st.session_state["show_custom_search"] 

    with st.expander("⚙️ Search Settings", expanded=st.session_state["show_custom_search"]): 
        col1, col2 = st.columns(2) 
        with col1: 
            custom_role = st.text_input("Job Title / Role", placeholder="e.g. Head of Talent Acquisition") 
            custom_location = st.text_input("Location", placeholder="e.g. Spain, Europe, India") 
            track = st.selectbox("Track", ["A - India Based (EU-facing)", "B - Europe Direct", "Both"]) 
        with col2: 
            min_score_filter = st.slider("Minimum Score to Save", 0, 100, 50) 
            max_results = st.selectbox("Max Results", [25, 50, 100, 200], index=1) 
            seniority = st.multiselect("Seniority Level", 
                ["Director", "Head", "VP", "Senior Manager", "Manager", "Associate Director", "Lead"], 
                default=["Director", "Head", "VP", "Senior Manager", "Associate Director"] 
            ) 
        
        keywords_extra = st.text_input("Additional Keywords (comma separated)", 
            placeholder="e.g. RPO, pharma, EMEA") 
        sources = st.multiselect(
            "Job Sources",
            ["LinkedIn", "Google Jobs (Naukri/Indeed/All sites)"],
            default=["LinkedIn", "Google Jobs (Naukri/Indeed/All sites)"],
        ) 

    col_a, col_b, col_c, col_d = st.columns(4) 
    with col_a: 
        if st.button("▶ Run Custom Search"): 
            before_jobs = get_all_jobs() 
            before_ids = {j["id"] for j in before_jobs} 
            with st.spinner("Searching all sources..."): 
                profile = json.load(open('profile.json')) 
                extra_kw = [k.strip() for k in keywords_extra.split(',') if k.strip()] 
                track_val = "A" if "A" in track else ("B" if "B" in track else "both") 
                total = 0 

                if "LinkedIn" in sources: 
                    from scrapers.scraper_linkedin import scrape_linkedin_custom 
                    count = scrape_linkedin_custom( 
                        role=custom_role or None, 
                        location=custom_location or None, 
                        track=track_val, 
                        seniority_filters=seniority, 
                        extra_keywords=extra_kw, 
                        max_results=max_results 
                    ) 
                    total += count 
                    st.info(f"LinkedIn: {count} jobs") 

                if "Google Jobs (Naukri/Indeed/All sites)" in sources: 
                    import scrapers.scraper_google_jobs as gj 
                    if not getattr(gj, "SERPAPI_KEY", None): 
                        st.warning("Google Jobs search not configured — SERPAPI_KEY missing in .env") 
                    else: 
                        query = custom_role or "talent acquisition manager" 
                        location = custom_location or "Europe" 
                        count = gj.scrape_custom_google_jobs(query, location, track_val, extra_kw) 
                        total += count 
                        st.info(f"Google Jobs: {count} jobs") 

                after_jobs = get_all_jobs() 
                new_ids = [j["id"] for j in after_jobs if j["id"] not in before_ids] 
                st.session_state["latest_search_job_ids"] = new_ids 
                st.success(f"✅ Total: {total} new jobs found!") 
                st.rerun() 

    with col_b: 
        if st.button("▶ Run Default Search"): 
            before_jobs = get_all_jobs() 
            before_ids = {j["id"] for j in before_jobs} 
            with st.spinner("Running default searches..."): 
                from scrapers.scraper_linkedin import scrape_linkedin 
                count = scrape_linkedin() 
                after_jobs = get_all_jobs() 
                new_ids = [j["id"] for j in after_jobs if j["id"] not in before_ids] 
                st.session_state["latest_search_job_ids"] = new_ids 
                st.success(f"✅ Found {count} jobs!") 
                st.rerun() 

    with col_c: 
        if st.button("🧠 Score Unscored Jobs"): 
            with st.spinner("Scoring with Groq..."): 
                from engines.gemini_engine import score_job 
                profile = json.load(open('profile.json')) 
                jobs = get_all_jobs() 
                unscored = [j for j in jobs if j['score'] == 0] 
                scored = 0 
                for job in unscored[:20]: 
                    result = score_job(job['description'], profile) 
                    update_job_score(job['id'], result['score'], result['reason']) 
                    scored += 1 
                st.success(f"✅ Scored {scored} jobs!") 
                st.rerun() 
    with col_d: 
        if st.button("🌐 Google Jobs Search"): 
            before_jobs = get_all_jobs() 
            before_ids = {j["id"] for j in before_jobs} 
            with st.spinner("Searching Google Jobs..."): 
                import scrapers.scraper_google_jobs as gj 
                if not getattr(gj, "SERPAPI_KEY", None): 
                    st.warning("Google Jobs search not configured — SERPAPI_KEY missing in .env") 
                    count = 0 
                else: 
                    count = gj.scrape_all_google_jobs() 
                after_jobs = get_all_jobs() 
                new_ids = [j["id"] for j in after_jobs if j["id"] not in before_ids] 
                st.session_state["latest_search_job_ids"] = new_ids 
                st.success(f"✅ {count} jobs from Google Jobs!") 
                st.rerun() 

    if "latest_search_job_ids" in st.session_state and st.session_state["latest_search_job_ids"]: 
        st.markdown("---") 
        st.subheader("🆕 Jobs from your last search") 
        all_jobs = get_all_jobs() 
        latest_ids = set(st.session_state["latest_search_job_ids"]) 
        latest_jobs = [j for j in all_jobs if j["id"] in latest_ids] 
        st.caption(f"Showing {len(latest_jobs)} jobs from the last search") 
        for job in latest_jobs[:100]: 
            render_job_body(job) 

    st.markdown("---") 
    stats = get_stats() 
    c1,c2,c3,c4 = st.columns(4) 
    with c1: 
        st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["jobs_today"]}</div><div class="metric-label">🔍 Jobs Found Today</div></div>',unsafe_allow_html=True) 
    with c2: 
        st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["applied_week"]}</div><div class="metric-label">✅ Applied This Week</div></div>',unsafe_allow_html=True) 
    with c3: 
        st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["awaiting_review"]}</div><div class="metric-label">⏳ Awaiting Review</div></div>',unsafe_allow_html=True) 
    with c4: 
        st.markdown(f'<div class="metric-card"><div class="metric-value">{stats["interviews_scheduled"]}</div><div class="metric-label">🎤 Interviews Scheduled</div></div>',unsafe_allow_html=True) 
    st.markdown("---") 
    st.subheader("📊 Recent Applications") 
    jobs = get_all_jobs() 
    applied = [j for j in jobs if j['status']=='applied'] 
    if applied: 
        df = pd.DataFrame(applied)[['company','title','track','status','date_applied','score']] 
        df.columns = ['Company','Role','Track','Status','Date Applied','Score'] 
        st.dataframe(df,use_container_width=True,hide_index=True) 
    else: 
        st.info("No applications yet. Find jobs in the 💼 Jobs tab!") 
    st.markdown("---") 
    st.subheader("🔥 Top Matches Today") 
    jobs = get_all_jobs() 
    top = sorted([j for j in jobs if j['score']>0],key=lambda x:x['score'],reverse=True)[:5] 
    if top: 
        for j in top: 
            if j['score'] >= 80: 
                match_label = "🔥 High match" 
            elif j['score'] >= 60: 
                match_label = "👍 Good match" 
            elif j['score'] > 0: 
                match_label = "👌 Light match" 
            else: 
                match_label = "No score yet" 
            card_html = f""" 
            <div class="job-card"> 
                <div class="job-card-header"> 
                    <div class="job-card-title">{j['title']}</div> 
                    <div class="job-card-score">{j['score']}</div> 
                </div> 
                <div class="job-card-company">{j['company']}</div> 
                <div class="job-card-meta">{j['location']} • Track {j['track']}</div> 
                <div class="job-card-tag">{match_label}</div> 
            </div> 
            """ 
            st.markdown(card_html, unsafe_allow_html=True) 
            btn_col_1, btn_col_2 = st.columns([1, 2]) 
            with btn_col_1: 
                if j.get('url'): 
                    st.markdown(f"[🔗 View direct on LinkedIn]({j['url']})") 
                else: 
                    st.caption("No LinkedIn link available") 
            with btn_col_2: 
                render_job_body(j) 
    else: 
        st.info("Run scorer to see top matches here once jobs are scraped and scored.") 
elif page == "💼 Jobs": 
    st.title("💼 Job Listings") 
    st.markdown("---") 
    jobs = get_all_jobs() 
    if not jobs: 
        st.warning("No jobs found yet. Go to Home and run the scraper first.") 
    else: 
        latest_ids = set(st.session_state.get("latest_search_job_ids", []) or []) 
        view_mode = st.radio("Jobs to show", ["All jobs", "Only from last search"], horizontal=True) 
        c1,c2,c3 = st.columns(3) 
        with c1: 
            track_filter = st.selectbox("Track",["All","A - India Based","B - Europe Direct","India - All India jobs"]) 
        with c2: 
            status_filter = st.selectbox("Status",["All","new","approved","rejected","applied"]) 
        with c3: 
            min_score = st.slider("Min Score",0,100,0) 
        base_jobs = jobs 
        if view_mode == "Only from last search": 
            if latest_ids: 
                base_jobs = [j for j in base_jobs if j["id"] in latest_ids] 
            else: 
                base_jobs = [] 
        filtered = base_jobs 
        if track_filter != "All": 
            if track_filter == "A - India Based": 
                filtered = [j for j in filtered if j["track"] == "A"] 
            elif track_filter == "B - Europe Direct": 
                filtered = [j for j in filtered if j["track"] == "B"] 
            elif track_filter == "India - All India jobs": 
                filtered = [j for j in filtered if "india" in str(j.get("location","")).lower()] 
        if status_filter != "All": 
            filtered = [j for j in filtered if j['status']==status_filter] 
        if min_score > 0: 
            filtered = [j for j in filtered if j['score']>=min_score] 
        active_filters = [] 
        if track_filter != "All": 
            active_filters.append(track_filter) 
        if status_filter != "All": 
            active_filters.append(status_filter) 
        if min_score > 0: 
            active_filters.append(f"Score ≥ {min_score}") 
        if active_filters: 
            prefix = "Last search" if view_mode == "Only from last search" else "All jobs" 
            st.caption(f"{prefix}: showing {len(filtered)} of {len(base_jobs)} jobs | " + " • ".join(active_filters)) 
        else: 
            prefix = "Last search" if view_mode == "Only from last search" else "All jobs" 
            st.caption(f"{prefix}: showing all {len(filtered)} jobs (no filters active)") 
        for job in filtered[:50]: 
            render_job_body(job) 

elif page == "📋 Applications": 
    st.title("📋 Applications Tracker") 
    st.markdown("---") 
    jobs = get_all_jobs() 
    applied = [j for j in jobs if j['status'] in ['applied','interview','offer']] 
    if not applied: 
        st.info("No applications tracked yet. Approve jobs and mark them as applied.") 
    else: 
        status_filter = st.selectbox("Filter by status", ["All", "Applied", "Interview", "Offer"]) 
        filtered_apps = applied 
        if status_filter != "All": 
            key_map = {"Applied": "applied", "Interview": "interview", "Offer": "offer"} 
            status_key = key_map[status_filter] 
            filtered_apps = [j for j in applied if j['status'] == status_key] 
        if not filtered_apps: 
            st.info("No applications for this filter yet.") 
        else: 
            df = pd.DataFrame(filtered_apps) 
            order_map = {'offer': 0, 'interview': 1, 'applied': 2} 
            df['status_order'] = df['status'].map(order_map).fillna(3) 
            df = df.sort_values(by=['status_order', 'date_applied', 'company'], ascending=[True, False, True]) 
            caption_label = "all statuses" if status_filter == "All" else status_filter 
            st.caption(f"Showing {len(filtered_apps)} of {len(applied)} tracked applications | {caption_label}") 
            df_view = df[['company','title','location','track','status','date_applied','score']] 
            df_view.columns = ['Company','Role','Location','Track','Status','Date Applied','Score'] 
            status_map = {'applied': '✅ Applied', 'interview': '🎤 Interview', 'offer': '🏆 Offer'} 
            df_view['Status'] = df_view['Status'].map(lambda s: status_map.get(s, s)) 
            st.dataframe(df_view,use_container_width=True,hide_index=True) 


elif page == "📣 Outreach":
    st.title("📣 LinkedIn Outreach")
    st.markdown("---")
    from engines.database import (
        get_hiring_targets_by_status,
        insert_hiring_targets,
        update_hiring_target_status,
        update_hiring_target_message_flag,
        create_hiring_targets_table,
    )
    create_hiring_targets_table()

    if st.button("🎯 Generate Today's Hiring Manager Targets"):
        with st.spinner("Searching LinkedIn for relevant hiring managers..."):
            try:
                from engines.outreach_agent import find_hiring_managers
                from engines.database import get_all_jobs
                import json as jmod

                profile = jmod.load(open("profile.json"))
                jobs = get_all_jobs()
                top_jobs = sorted(
                    [j for j in jobs if j["score"] >= 70],
                    key=lambda x: x["score"],
                    reverse=True,
                )[:6]

                search_targets = []
                if top_jobs:
                    for job in top_jobs:
                        search_targets.append(
                            (job["company"], job["title"], job.get("id", 0))
                        )
                    st.info(f"Using {len(top_jobs)} top-scored jobs")
                else:
                    st.info("No scored jobs found — using profile targets")
                    for role in profile.get("target_roles", [])[:3]:
                        for market in profile.get("target_markets", [])[:2]:
                            search_targets.append((market, role, 0))

                all_rows = []
                errors_all = []
                for company, role, job_id in search_targets[:5]:
                    st.write(f"🔍 Searching: {company} — {role}")
                    contacts, errors = find_hiring_managers(company, role, max_results=2)
                    errors_all.extend(errors)
                    for c in contacts:
                        c["job_id"] = job_id
                        c["date_added"] = date.today().isoformat()
                        all_rows.append(c)
                    if len(all_rows) >= 10:
                        break

                if all_rows:
                    inserted = insert_hiring_targets(all_rows)
                    st.success(
                        f"✅ Found {len(all_rows)} hiring managers! {inserted} new added."
                    )
                else:
                    st.warning("No suitable hiring managers found.")
                    if errors_all:
                        st.error("Errors: " + " | ".join(errors_all[:3]))
            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.markdown("---")

    st.subheader("🆕 New Targets")
    new_targets = get_hiring_targets_by_status("new")
    if not new_targets:
        st.info("No new hiring manager targets yet. Click Generate above.")
    for t in new_targets:
        with st.expander(
            f"👤 {t['contact_name']} — {t.get('contact_role') or t.get('contact_title') or ''} at {t['company']}"
        ):
            st.markdown(f"[View LinkedIn Profile]({t['linkedin_url']})")
            profile = json.load(open("profile.json"))
            if st.button("✍️ Generate Message", key=f"gm_{t['id']}"):
                from dotenv import load_dotenv
                load_dotenv()
                from engines.outreach_agent import generate_outreach_message
                from groq import Groq

                groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                msg = generate_outreach_message(
                    t["contact_name"],
                    t["company"],
                    t.get("contact_role") or t.get("contact_title") or "",
                    profile,
                    groq_client,
                )
                st.session_state[f"omsg_{t['id']}"] = msg
            if f"omsg_{t['id']}" in st.session_state:
                edited = st.text_area(
                    "Message (max 280):",
                    value=st.session_state[f"omsg_{t['id']}"],
                    max_chars=280,
                    key=f"oedit_{t['id']}",
                )
                st.caption(f"{len(edited)}/280 characters")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🚀 Send Request", key=f"osr_{t['id']}"):
                        import subprocess
                        import tempfile
                        import json as jmod

                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=".json", delete=False
                        ) as f:
                            jmod.dump(
                                {"url": t["linkedin_url"], "message": edited}, f
                            )
                            tmp = f.name
                        subprocess.Popen(
                            [
                                "python3",
                                "-c",
                                "import json; from engines.outreach_agent import send_connection_request; d=json.load(open(%r)); send_connection_request(d['url'], d['message'])"
                                % tmp,
                            ]
                        )
                        update_hiring_target_status(t["id"], "pending")
                        st.success("✅ Request sent! Marked as pending.")
                        st.rerun()
                with col2:
                    if st.button("⏭️ Skip", key=f"skip_{t['id']}"):
                        update_hiring_target_status(t["id"], "skipped")
                        st.rerun()

    st.markdown("---")

    st.subheader("⏳ Pending Connections")
    pending = get_hiring_targets_by_status("pending")
    if not pending:
        st.info("No pending connection requests.")
    for t in pending:
        with st.expander(f"⏳ {t['contact_name']} — {t['company']}"):
            st.markdown(f"[View Profile]({t['linkedin_url']})")
            if st.button("✅ Connection Accepted", key=f"acc_{t['id']}"):
                update_hiring_target_status(t["id"], "connected")
                st.rerun()

    st.markdown("---")

    st.subheader("🤝 Connected")
    connected = get_hiring_targets_by_status("connected")
    if not connected:
        st.info("No connected hiring managers tracked yet.")
    for t in connected:
        with st.expander(f"🤝 {t['contact_name']} — {t['company']}"):
            st.markdown(f"[View Profile]({t['linkedin_url']})")
            sent = t.get("message_sent", 0)
            if not sent:
                if st.button("📨 Mark Message Sent", key=f"ms_{t['id']}"):
                    update_hiring_target_message_flag(t["id"], 1)
                    st.rerun()
            else:
                st.success("✅ Message sent")


elif page == "📈 Insights":
    st.title("📈 Insights")
    st.markdown("---")
    jobs = get_all_jobs()
    if not jobs:
        st.info("No jobs in the database yet. Run a search from Home first.")
    else:
        df = pd.DataFrame(jobs)
        total_jobs = len(df)
        applied_count = (df["status"] == "applied").sum()
        interview_count = (df["status"] == "interview").sum()
        offer_count = (df["status"] == "offer").sum()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Jobs tracked", total_jobs)
        with col2:
            st.metric("Applied", applied_count)
        with col3:
            st.metric("Interviews", interview_count)
        with col4:
            st.metric("Offers", offer_count)
        st.markdown("---")
        if "score" in df.columns:
            track_scores = df[df["score"] > 0].groupby("track")["score"].mean().reset_index()
            track_scores["track"] = track_scores["track"].map({"A": "Track A (India-based)", "B": "Track B (Europe)"})
            st.subheader("Average score by track")
            st.bar_chart(track_scores.set_index("track"))
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        st.subheader("Jobs by status")
        st.bar_chart(status_counts.set_index("status"))

elif page == "📁 CV Vault": 
    st.title("📁 CV Vault") 
    st.markdown("---") 
    import os 
    app_dir = "applications" 
    if not os.path.exists(app_dir) or not os.listdir(app_dir): 
        st.info("No CVs generated yet. Go to 💼 Jobs and click Generate CV on any job.") 
    else: 
        folders = sorted(os.listdir(app_dir), reverse=True) 
        st.caption(f"{len(folders)} application packages generated") 
        for folder in folders: 
            folder_path = f"{app_dir}/{folder}" 
            if os.path.isdir(folder_path): 
                files = os.listdir(folder_path) 
                cv_files = [f for f in files if f.endswith('.pdf') and 'CV_' in f] 
                cl_files = [f for f in files if f.endswith('.pdf') and 'Cover' in f] 
                with st.expander(f"📁 {folder}"): 
                    col1, col2 = st.columns(2) 
                    with col1: 
                        if cv_files: 
                            st.markdown(f"📄 **CV:** {cv_files[0]}") 
                        if cl_files: 
                            st.markdown(f"✉️ **Cover Letter:** {cl_files[0]}") 
                    with col2: 
                        jd_file = f"{folder_path}/JobDetails.txt" 
                        if os.path.exists(jd_file): 
                            with open(jd_file) as f: 
                                details = f.read() 
                            st.text(details[:200]) 

elif page == "🎤 Interview Prep": 
    st.title("🎤 Interview Prep") 
    st.markdown("---") 
    jobs = get_all_jobs() 
    applied = [j for j in jobs if j['status'] in ['applied', 'approved', 'interview']] 
    if not applied: 
        st.info("No applications yet. Approve or apply to jobs first.") 
    else: 
        options = {f"{j['title']} at {j['company']} ({j['location']})": j for j in applied} 
        selected = st.selectbox("Select a job to prepare for:", list(options.keys())) 
        job = options[selected] 
 
        col1, col2 = st.columns(2) 
        with col1: 
            st.markdown(f"**Company:** {job['company']}") 
            st.markdown(f"**Role:** {job['title']}") 
        with col2: 
            st.markdown(f"**Location:** {job['location']}") 
            st.markdown(f"**Score:** {job['score']}") 
 
        st.markdown("---") 
 
        # Check if prep pack already exists 
        import os 
        prep_file = f"prep_packs/{job['company'].replace(' ','_')}_{job['title'].replace(' ','_')[:20]}_prep.json" 
 
        if os.path.exists(prep_file): 
            st.success("✅ Prep pack already generated!") 
            with open(prep_file) as f: 
                prep = json.load(f) 
        else: 
            prep = None 
 
        if st.button("🎯 Generate Interview Prep Pack"): 
            with st.spinner("Generating your personalised prep pack with Groq..."): 
                from engines.gemini_engine import generate_interview_prep 
                profile = json.load(open('profile.json')) 
                prep = generate_interview_prep( 
                    job['company'], job['title'], 
                    job['description'], 
                    profile.get('cv_summary', ''), 
                    profile 
                ) 
                if 'error' not in prep: 
                    os.makedirs('prep_packs', exist_ok=True) 
                    with open(prep_file, 'w') as f: 
                        json.dump(prep, f, indent=2) 
                    st.success("✅ Prep pack ready!") 
                    update_job_status(job['id'], 'interview') 
 
        if prep and 'error' not in prep: 
            st.markdown("---") 
            st.subheader("🏢 Company Brief") 
            st.write(prep.get('company_brief', '')) 
 
            st.subheader("🎯 Key Themes to Prepare") 
            for theme in prep.get('key_themes', []): 
                st.markdown(f"• {theme}") 
 
            st.markdown("---") 
            st.subheader("❓ Interview Questions & Suggested Answers") 
            for i, q in enumerate(prep.get('questions', [])): 
                with st.expander(f"Q{i+1}: {q['question']}"): 
                    st.markdown(f"**💡 Suggested Answer:**") 
                    st.write(q['suggested_answer']) 
 
            st.markdown("---") 
            st.subheader("💬 Questions to Ask Them") 
            for q in prep.get('questions_to_ask', []): 
                st.markdown(f"• {q}") 
 
            if prep.get('red_flags_to_address'): 
                st.markdown("---") 
                st.subheader("⚠️ Potential Concerns to Address") 
                for flag in prep.get('red_flags_to_address', []): 
                    st.markdown(f"• {flag}") 

elif page == "⚙️ Settings": 
    st.title("⚙️ Settings") 
    st.markdown("---") 
    try: 
        profile = json.load(open('profile.json')) 
        st.subheader("Your Profile") 
        st.json(profile) 
    except: 
        st.error("profile.json not found")
