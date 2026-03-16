import streamlit as st 
import pandas as pd 
import json 
import os 
from engines.database import init_db, get_all_jobs, get_stats, update_job_status, update_job_score 
from datetime import datetime, date 
 
st.set_page_config(page_title="Job Hunt Assistant", page_icon="🎯", layout="wide") 
 
st.markdown("""<style> 
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&display=swap');

/* Base Styles & Animated Background */
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif !important; }

[data-testid="stAppViewContainer"] {
    background: linear-gradient(-45deg, #09090e, #130f24, #0d1b2a, #110517);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
    color: #f0f0f5;
}

@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Sidebar Styling */
[data-testid="stSidebar"] {
    background: rgba(10, 5, 20, 0.4) !important;
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    box-shadow: 5px 0 30px rgba(0,0,0,0.5);
}
[data-testid="stSidebar"] * { color: #e0e0ea !important; }
[data-testid="stSidebarNav"] { padding-top: 2rem; }

/* Header / Top Nav */
[data-testid="stHeader"] { background-color: transparent !important; }

/* Metric Cards with Glowing Border Effect */
.metric-card {
    position: relative;
    background: rgba(20, 20, 35, 0.4);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 10px 40px -10px rgba(0,0,0,0.5);
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    overflow: hidden;
    animation: fadeUp 0.8s ease-out forwards;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: -100%; width: 50%; height: 100%;
    background: linear-gradient(to right, transparent, rgba(255,255,255,0.05), transparent);
    transform: skewX(-20deg);
    transition: 0.5s;
}
.metric-card:hover::before { left: 150%; }

.metric-card:hover {
    transform: translateY(-8px) scale(1.02);
    border-color: rgba(0, 255, 204, 0.4);
    box-shadow: 0 15px 50px -10px rgba(0, 255, 204, 0.2);
}

.metric-value {
    font-size: 3.5em;
    font-weight: 700;
    background: linear-gradient(135deg, #00FFCC 0%, #00BFFF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(0, 255, 204, 0.3);
}

.metric-label {
    font-size: 1.1em;
    font-weight: 600;
    color: #94a3b8;
    margin-top: 10px;
    text-transform: uppercase;
    letter-spacing: 2px;
}

/* Animations */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Buttons */
.stButton>button {
    background: linear-gradient(45deg, #FF3366, #FF9933) !important;
    background-size: 200% auto !important;
    color: white !important;
    border: none;
    border-radius: 14px;
    font-weight: 700;
    padding: 0.8rem 1.5rem;
    font-size: 1.1em;
    letter-spacing: 1px;
    transition: all 0.4s ease;
    box-shadow: 0 8px 25px rgba(255, 51, 102, 0.3);
    text-transform: uppercase;
    width: 100%;
}

.stButton>button:hover {
    background-position: right center !important;
    transform: translateY(-3px) scale(1.01);
    box-shadow: 0 12px 30px rgba(255, 51, 102, 0.5);
}

.stButton>button:active { transform: translateY(1px); }

/* Expanders */
[data-testid="stExpander"] {
    background: rgba(30, 30, 50, 0.3) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    transition: all 0.3s ease;
    margin-bottom: 1rem;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(255, 255, 255, 0.15) !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
}
[data-testid="stExpander"] summary {
    padding: 1rem !important;
    font-size: 1.1em;
    font-weight: 600;
}

/* Typography */
h1 {
    font-size: 3rem !important;
    font-weight: 700 !important;
    background: linear-gradient(to right, #ffffff, #a5b4fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
    margin-bottom: 20px !important;
}

h2, h3 { font-weight: 600 !important; color: #e2e8f0 !important; letter-spacing: -0.5px; }
p, label { color: #cbd5e1 !important; line-height: 1.6; }

/* Custom Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }

/* DataFrame Styling */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
    overflow: hidden;
    background: rgba(20, 20, 35, 0.4);
}
hr { border-color: rgba(255, 255, 255, 0.05) !important; margin: 2rem 0 !important; }
</style>""", unsafe_allow_html=True) 
 
init_db() 
page = st.sidebar.radio("🎯 Job Hunt Assistant", ["🏠 Home","💼 Jobs","📋 Applications","📁 CV Vault","🎤 Interview Prep","⚙️ Settings"])


if page == "🏠 Home": 
    st.title("Welcome back, Danish! 👋") 
    st.caption(f"Today is {datetime.now().strftime('%A, %d %B %Y')}") 
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
    col1,col2 = st.columns(2) 
    with col1: 
        st.subheader("📊 Recent Applications") 
        jobs = get_all_jobs() 
        applied = [j for j in jobs if j['status']=='applied'] 
        if applied: 
            df = pd.DataFrame(applied)[['company','title','track','status','date_applied','score']] 
            df.columns = ['Company','Role','Track','Status','Date Applied','Score'] 
            st.dataframe(df,use_container_width=True,hide_index=True) 
        else: 
            st.info("No applications yet. Find jobs in the 💼 Jobs tab!") 
    with col2: 
        st.subheader("🔥 Top Matches Today") 
        jobs = get_all_jobs() 
        top = sorted([j for j in jobs if j['score']>0],key=lambda x:x['score'],reverse=True)[:5] 
        if top: 
            for j in top: 
                st.markdown(f"**{j['title']}** — {j['company']}") 
                st.caption(f"Score: {j['score']} | {j['location']} | Track {j['track']}") 
                st.markdown("---") 
        else: 
            st.info("Run scorer to see top matches here once jobs are scraped and scored.") 
    st.markdown("---") 
    col_a,col_b = st.columns(2) 
    with col_a: 
        if st.button("▶ Run LinkedIn Scraper"): 
            with st.spinner("Scraping LinkedIn jobs..."): 
                from scrapers.scraper_linkedin import scrape_linkedin 
                count = scrape_linkedin() 
                st.success(f"✅ Found {count} new jobs!") 
                st.rerun() 
    with col_b: 
        if st.button("🧠 Score Unscored Jobs"): 
            with st.spinner("Scoring with Gemini..."): 
                from engines.gemini_engine import score_job 
                profile = json.load(open('profile.json')) 
                jobs = get_all_jobs() 
                unscored = [j for j in jobs if j['score']==0] 
                scored = 0 
                for job in unscored[:20]: 
                    result = score_job(job['description'],profile) 
                    update_job_score(job['id'],result['score'],result['reason']) 
                    scored += 1 
                st.success(f"✅ Scored {scored} jobs!") 
                st.rerun()

elif page == "💼 Jobs": 
    st.title("💼 Job Listings") 
    st.markdown("---") 
    jobs = get_all_jobs() 
    if not jobs: 
        st.warning("No jobs found yet. Go to Home and run the scraper first.") 
    else: 
        c1,c2,c3 = st.columns(3) 
        with c1: 
            track_filter = st.selectbox("Track",["All","A - India Based","B - Europe Direct"]) 
        with c2: 
            status_filter = st.selectbox("Status",["All","new","approved","rejected","applied"]) 
        with c3: 
            min_score = st.slider("Min Score",0,100,0) 
        filtered = jobs 
        if track_filter != "All": 
            tv = "A" if "A" in track_filter else "B" 
            filtered = [j for j in filtered if j['track']==tv] 
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
            st.caption(f"Showing {len(filtered)} of {len(jobs)} jobs | " + " • ".join(active_filters)) 
        else: 
            st.caption(f"Showing all {len(filtered)} jobs (no filters active)") 
        for job in filtered[:50]: 
            status_emoji = {'new': '🔵', 'approved': '🟢', 'rejected': '🔴', 'applied': '✅', 'interview': '🎤'}.get(job['status'], '🔵') 
            if job['score'] >= 80: 
                match_label = "🔥 High match" 
            elif job['score'] >= 60: 
                match_label = "👍 Good match" 
            elif job['score'] > 0: 
                match_label = "👌 Light match" 
            else: 
                match_label = "No score yet" 
            header_text = f"{status_emoji} {job['title']} — {job['company']} | {match_label} ({job['score']}) | Track {job['track']} | {job['status'].upper()}" 
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
                        safe_company = job['company'].replace(' ','_')[:30] 
                        safe_role = job['title'].replace(' ','_')[:25] 
                        folder = f"applications/{safe_company}_{safe_role}_{date.today().strftime('%d%b%Y')}" 
                        cv_files = [] 
                        if os.path.exists(folder): 
                            cv_files = [f for f in os.listdir(folder) if f.endswith('.pdf') and 'CV_' in f] 
                        if not cv_files: 
                            st.warning("⚠️ Generate CV first!") 
                        else: 
                            cv_path = f"{folder}/{cv_files[0]}" 
                            profile = json.load(open('profile.json')) 
                            st.info("🌐 Opening LinkedIn... Click the GREEN submit button!") 
                            from engines.apply_agent import launch_apply 
                            success, message = launch_apply(dict(job), cv_path, profile) 
                            if success: 
                                st.success("✅ Browser opening... Check your screen!") 
                                update_job_status(job['id'], 'applied') 
                            else: 
                                st.warning(f"ℹ️ {message}") 

                st.markdown("---") 
                st.markdown("---") 
                st.markdown("**📧 Email Application**") 
                e1, e2 = st.columns(2) 
                with e1: 
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
 
                st.markdown("**🤝 LinkedIn Outreach**") 
                st.caption("Find a warm human contact and send a tailored connection request.") 
                c_a, c_b = st.columns(2) 
                with c_a: 
                    if st.button("🔍 Find Contact", key=f"find_{job['id']}"): 
                        with st.spinner("Searching LinkedIn..."): 
                            from engines.outreach_agent import find_company_contact 
                            contacts = find_company_contact(job['company']) 
                            if contacts: 
                                st.session_state[f"contacts_{job['id']}"] = contacts 
                                st.success(f"Found {len(contacts)} contact(s)!") 
                            else: 
                                st.warning("No contacts found") 

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
