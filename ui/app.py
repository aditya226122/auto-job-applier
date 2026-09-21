import streamlit as st
import pandas as pd
import json
import datetime
import os
import sys
from pathlib import Path

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.db import db
from services.notifier import notifier
from engine.matcher import matcher
from engine.applier import job_applier
from engine.job_searcher import job_searcher
import config

st.set_page_config(
    page_title="AI Job Application Agent | Udaya Lakshmi Boddu",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Autonomous Job Application Agent")
st.caption("Custom AI Agent for **Udaya Lakshmi Boddu** &bull; Rate: **1 to 3 Fresher Jobs Every Hour** (Target: **24 Jobs/Day**) &bull; Instant Proof Emails to `udayalakshmiboddu83@gmail.com`")

# Top metrics
col1, col2, col3, col4 = st.columns(4)
today_count = db.get_today_applied_count()
all_apps = db.get_all_applications(limit=200)
applied_total = len([a for a in all_apps if a.get("status") == "APPLIED"])

with col1:
    st.metric("Applied Today", f"{today_count} / {config.MAX_DAILY_APPLICATIONS}", delta=f"{today_count} applied")
with col2:
    st.metric("Daily Target", f"Up to {config.MAX_DAILY_APPLICATIONS} Jobs / Day")
with col3:
    st.metric("Total Jobs Applied (Lifetime)", str(applied_total))
with col4:
    st.metric("Live Recipient Email", "udayalakshmiboddu83@gmail.com")

st.markdown("---")

# Control Center
st.subheader("⚡ Agent Control Center")

if "last_run_msg" in st.session_state:
    st.success(st.session_state["last_run_msg"])
    del st.session_state["last_run_msg"]
if "last_run_info" in st.session_state:
    st.info(st.session_state["last_run_info"])
    del st.session_state["last_run_info"]

ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1.5, 1.5, 1])

with ctrl_col1:
    if st.button("⏰ Trigger Hourly Run (1-3 Jobs Now)", type="primary", use_container_width=True):
        with st.spinner(f"Agent applying for fresher jobs (1 Open ATS + Direct Company Portals) & sending live proof emails..."):
            results = job_applier.run_hourly_application_batch()
            if results:
                ats_c = sum(1 for j in results if j.get("is_open_ats"))
                direct_c = sum(1 for j in results if not j.get("is_open_ats"))
                st.session_state["last_run_msg"] = f"🎉 Successfully applied to {len(results)} jobs ({ats_c} Open ATS + {direct_c} Direct Company Portals)! Instant proof emails dispatched to udayalakshmiboddu83@gmail.com."
            else:
                st.session_state["last_run_info"] = "Daily quota reached or all matching listings have already been applied for today."
        st.rerun()

with ctrl_col2:
    batch_size = st.selectbox("Trigger Custom Batch Size:", options=[3, 5, 10, 15, 20, 24], index=1)
    if st.button("🚀 Trigger Full Batch", use_container_width=True):
        with st.spinner(f"Agent applying for up to {batch_size} fresher jobs..."):
            results = job_applier.run_daily_application_batch(target_count=batch_size)
            if results:
                ats_c = sum(1 for j in results if j.get("is_open_ats"))
                direct_c = sum(1 for j in results if not j.get("is_open_ats"))
                st.session_state["last_run_msg"] = f"🎉 Successfully applied to {len(results)} jobs ({ats_c} Open ATS + {direct_c} Direct Portals)! Confirmation emails dispatched."
            else:
                st.session_state["last_run_info"] = "Daily quota reached or matching listings processed."
        st.rerun()

with ctrl_col3:
    if st.button("📧 Send Test Email", use_container_width=True):
        sample_job = {
            "title": "Graduate Trainee Engineer - IoT & Software",
            "company": "Tata Consultancy Services (TCS)",
            "location": "Hyderabad, India",
            "portal": "TCS iON",
            "job_url": "https://www.tcs.com/careers"
        }
        res = notifier.send_single_application_alert(sample_job, 95, "Test Application via Dashboard")
        st.toast("Email sent to udayalakshmiboddu83@gmail.com!" if res else "Check SMTP settings in .env")

from engine.inbox_listener import inbox_verifier

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Applied Jobs History", 
    "🔍 Discover Company Portals", 
    "👤 Candidate Profile", 
    "📬 Verified Company Emails"
])

with tab1:
    st.subheader("Application Logs & Verified Proof of Submission")
    if all_apps:
        df = pd.DataFrame(all_apps)
        
        # --- Filters Section ---
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.5, 1.5, 1.5, 1.5])
        
        # Extract unique dates and portals
        unique_dates = sorted([str(d) for d in df["applied_date"].dropna().unique() if str(d).strip() != ""], reverse=True)
        date_options = ["All Dates"] + unique_dates

        unique_portals = sorted([str(p) for p in df["portal"].dropna().unique() if str(p).strip() != ""])
        portal_options = ["All Portals"] + unique_portals
        
        with filter_col1:
            selected_date = st.selectbox("📅 Filter by Applied Date:", options=date_options, index=0)

        with filter_col2:
            selected_portal = st.selectbox("🏢 Filter by Company Portal:", options=portal_options, index=0)
            
        with filter_col3:
            status_options = ["All Statuses"] + sorted([str(s) for s in df["status"].dropna().unique()])
            selected_status = st.selectbox("📌 Filter by Status:", options=status_options, index=0)
            
        with filter_col4:
            search_kw = st.text_input("🔍 Search Company / Role:", "")

        # Apply Filters
        filtered_df = df.copy()
        if selected_date != "All Dates":
            filtered_df = filtered_df[filtered_df["applied_date"] == selected_date]
        if selected_portal != "All Portals":
            filtered_df = filtered_df[filtered_df["portal"] == selected_portal]
        if selected_status != "All Statuses":
            filtered_df = filtered_df[filtered_df["status"] == selected_status]
        if search_kw:
            filtered_df = filtered_df[
                filtered_df["company"].str.contains(search_kw, case=False, na=False) |
                filtered_df["title"].str.contains(search_kw, case=False, na=False)
            ]

        # Filtered Count Indicator
        st.caption(f"Showing **{len(filtered_df)}** records across direct company career portals & ATS systems.")

        cols_to_show = [c for c in ["id", "title", "company", "location", "portal", "match_score", "reference_id", "status", "applied_date", "email_sent_status"] if c in filtered_df.columns]
        st.dataframe(filtered_df[cols_to_show], use_container_width=True)
        
        # --- Visual Confirmation & Proof Gallery for Filtered Records ---
        st.markdown(f"### 📸 Visual Confirmation & Proof Gallery {f'({selected_portal})' if selected_portal != 'All Portals' else ''}")
        filtered_records = filtered_df.to_dict(orient="records")
        proof_records = [app for app in filtered_records if app.get("status") == "APPLIED" and app.get("screenshot_path")]
        
        if proof_records:
            for app in proof_records:
                with st.expander(f"✔ Proof: {app.get('title')} @ {app.get('company')} [{app.get('portal', 'Direct Portal')}] - {app.get('applied_date')}"):
                    col_info, col_img = st.columns([1, 2])
                    with col_info:
                        st.write(f"**Company**: {app.get('company')}")
                        st.write(f"**Applied Role**: {app.get('title')}")
                        st.write(f"**Location**: {app.get('location')}")
                        st.write(f"**Platform / Portal**: `{app.get('portal')}`")
                        st.write(f"**Match Score**: {app.get('match_score')}%")
                        st.write(f"**Reference ID**: `{app.get('reference_id')}`")
                        st.write(f"**Applied Date**: `{app.get('applied_date')}`")
                        st.write(f"**Email Status**: {app.get('email_sent_status')}")
                    with col_img:
                        if os.path.exists(app.get("screenshot_path", "")):
                            st.image(app.get("screenshot_path"), caption=f"Verified Submission Receipt - {app.get('company')} ({app.get('portal')})")
        else:
            st.info(f"No proof screenshots found for the selected filter ({selected_portal} / {selected_date} / {selected_status}).")
    else:
        st.info("No job applications logged yet. Click 'Trigger Hourly Run' above to start!")

with tab2:
    st.subheader("🏢 Explore Direct Company Career Openings")
    st.caption("Fresh engineering graduate opportunities aggregated directly from official company career portals in India.")
    
    if st.button("🔄 Search Verified Company Portals"):
        with st.spinner(f"Querying verified direct career portals..."):
            fresh_jobs = job_searcher.search_fresher_jobs(limit=25)
            st.success(f"Found {len(fresh_jobs)} matching fresher roles on Direct Company Portals!")
            for j in fresh_jobs:
                score, reason = matcher.calculate_match_score(j)
                with st.expander(f"📌 [{j.get('portal')}] {j.get('title')} - {j.get('company')} ({score}% Match)"):
                    st.write(f"**Location**: {j.get('location')}")
                    st.write(f"**Platform / Portal**: `{j.get('portal')}`")
                    st.write(f"**Match Analysis**: {reason}")
                    st.write(f"**Description**: {j.get('description')}")
                    st.link_button(f"Open Official {j.get('company')} Career Page", j.get("job_url", "#"))

with tab3:
    st.subheader("Loaded Candidate Resume Profile")
    st.json(matcher.profile.data)

with tab4:
    st.subheader("📬 Verified Company-Side Confirmation Emails")
    st.caption("Live scan of your candidate inbox for official acknowledgment emails from company recruitment portals (e.g. TCS, Wipro, Infosys, Robert Bosch, LTTS, Siemens, ABB, Tata Power).")
    if st.button("🔄 Check Inbox for Company Confirmation Emails"):
        with st.spinner("Connecting to inbox and scanning for company confirmation messages..."):
            company_emails = inbox_verifier.check_incoming_company_confirmations(limit=15)
            if company_emails:
                st.success(f"Found {len(company_emails)} confirmation / recruitment messages from employers!")
                for em in company_emails:
                    with st.expander(f"🏢 {em.get('subject')} (From: {em.get('from_sender')})"):
                        st.write(f"**Sender**: `{em.get('from_sender')}`")
                        st.write(f"**Date**: `{em.get('date')}`")
                        st.info(em.get('snippet'))
            else:
                st.info("No recent recruitment acknowledgment emails found in your primary inbox yet. They will appear here automatically as companies process your applications!")


