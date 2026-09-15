# 🤖 Autonomous Job Application & Reporting Agent

Custom AI Agent tailored for **Udaya Lakshmi Boddu** (B.Tech EEE, JNTUK) to automatically search fresher jobs, apply for 10–15 jobs daily, and send instant notification emails to `udayalakshmiboddu83@gmail.com`.

---

## 🌟 Key Features

1. **Fresher Job Search Engine**:
   - Queries and aggregates entry-level openings (Graduate Engineer Trainee, Associate Software Engineer, Embedded Systems Trainee, IoT Developer, SQL Developer).
   - Tailored specifically to skills: C, Arduino, MATLAB, n8n, SQL, IoT cloud dashboards, and smart irrigation projects.

2. **Resume-Based AI Match & Form Answering**:
   - Automatically scores job relevance and answers custom employer questions (e.g., "Why should we hire you?", "Describe your IoT experience").

3. **Daily Application Limiter (10–15 Jobs/Day)**:
   - Built-in SQLite state tracking (`job_applications.db`) ensures you hit your target of 10 to 15 applications daily without duplicate submissions.

4. **Real-Time Email Notifications**:
   - Dispatches a formatted HTML alert to `udayalakshmiboddu83@gmail.com` immediately after each application is submitted.
   - Sends a daily summary breakdown of all jobs applied in that batch.

5. **Interactive Dashboard & Automated Scheduler**:
   - Streamlit Web Dashboard to track status, inspect matches, and trigger applications on-demand.
   - Background daemon scheduler to run automatically every morning.

---

## 🚀 Quick Start Guide

### 1. Configure Email & Environment
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Add your Gmail App Password to `.env` (Google Account -> Security -> 2-Step Verification -> App Passwords).

## ☁️ Running 24/7 Even When Laptop is Turned OFF

When your laptop is turned off, physical hardware cannot execute scripts. To run **24/7 continuously in the cloud for free**:

### Option 1: Free GitHub Actions Cloud Cron (Included)
We have included a pre-configured workflow at [`.github/workflows/job_applier_cron.yml`](.github/workflows/job_applier_cron.yml):
1. Push this project to your private GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Add 24/7 Job Application Agent"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/auto-job-applier.git
   git push -u origin main
   ```
2. In GitHub, go to **Settings -> Secrets and variables -> Actions** and add:
   - `SMTP_USER`: `adityachitti234@gmail.com`
   - `SMTP_PASSWORD`: `bqqoblxsxthdhryy`
   - `RECIPIENT_EMAIL`: `udayalakshmiboddu83@gmail.com`
3. GitHub Actions will now automatically wake up **every hour 24/7 in the cloud**, apply to 1-2 fresher jobs, and send emails to `udayalakshmiboddu83@gmail.com`—even when your laptop is completely powered off!

---

## 💻 Running Silently in Windows Background (Auto-Startup on Laptop)

The agent has been added to your Windows Startup folder:
- Every time your laptop boots up, the agent runs **100% invisibly in the background** without opening any terminal windows.
- To run silently right now without any windows, double-click [`launch_silent_background.vbs`](launch_silent_background.vbs).
