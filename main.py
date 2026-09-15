import argparse
import sys
import time
import datetime

# Fix Windows console encoding issues with emojis/unicode
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import schedule
    HAS_SCHEDULE = True
except ImportError:
    HAS_SCHEDULE = False
from engine.applier import job_applier
from services.db import db
from services.notifier import notifier
import config

def print_banner():
    print("""
========================================================================
   [AI] AUTONOMOUS FRESHER JOB APPLICATION AGENT
   Candidate: Udaya Lakshmi Boddu (B.Tech EEE, JNTUK)
   Recipient Email: udayalakshmiboddu83@gmail.com
   Target: 20 - 24 Freshers Jobs / Day (1-3 Jobs / Hour)
========================================================================
""")

def run_stats():
    today = datetime.date.today().isoformat()
    today_applied = db.get_today_applied_count()
    all_apps = db.get_all_applications(limit=20)
    
    print(f"\n📊 --- APPLICATION DASHBOARD STATS ---")
    print(f"📅 Today: {today}")
    print(f"🎯 Applied Today: {today_applied} / {config.MAX_DAILY_APPLICATIONS} (Target: {config.MIN_DAILY_APPLICATIONS}-15)")
    print(f"📁 Total Recorded Applications: {len(all_apps)}")
    print("\nRecent 5 Submissions:")
    for app in all_apps[:5]:
        print(f"  • [{app.get('status')}] {app.get('title')} @ {app.get('company')} ({app.get('match_score')}% Match) - {app.get('applied_date')}")
    print("---------------------------------------\n")

def test_email():
    print(f"\n📧 Sending test notification email to {config.RECIPIENT_EMAIL}...")
    sample_job = {
        "title": "Graduate Engineer Trainee - IoT & Software",
        "company": "Tata Consultancy Services (TCS)",
        "location": "Hyderabad, India",
        "portal": "TCS Careers",
        "job_url": "https://www.tcs.com/careers"
    }
    success = notifier.send_single_application_alert(
        job=sample_job, 
        match_score=95, 
        response_message="Test verification email - AI Agent Ready!"
    )
    if success:
        print("✅ Test email sent successfully!")
    else:
        print("❌ Failed to send test email. Check your SMTP settings in .env")

def schedule_hourly_agent():
    print("\n⏰ Hourly Background Scheduler Started!")
    print(f"The agent will automatically apply for 1-2 fresher jobs EVERY HOUR (Active: {config.ACTIVE_HOURS_START}:00 - {config.ACTIVE_HOURS_END}:00).")
    print(f"Immediate progress emails will be dispatched to {config.RECIPIENT_EMAIL} after each job is applied.")
    print("Press Ctrl+C to stop.")

    # Run the first hourly batch immediately upon launching
    print(f"\n🚀 Running initial hourly batch...")
    job_applier.run_hourly_application_batch()

    if HAS_SCHEDULE:
        schedule.every(1).hours.do(job_applier.run_hourly_application_batch)
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        # High reliability native timer loop (every 60 minutes)
        last_hour = datetime.datetime.now().hour
        while True:
            now = datetime.datetime.now()
            if now.hour != last_hour and (config.ACTIVE_HOURS_START <= now.hour <= config.ACTIVE_HOURS_END):
                print(f"\n[Hourly Scheduler] Triggering run for {now.strftime('%I:%M %p')}...")
                job_applier.run_hourly_application_batch()
                last_hour = now.hour
            time.sleep(30)

def main():
    parser = argparse.ArgumentParser(description="Autonomous Job Application Agent for Udaya Lakshmi Boddu")
    parser.add_argument("--apply", action="store_true", help="Run an immediate application batch (10-15 jobs)")
    parser.add_argument("--count", type=int, default=12, help="Number of jobs to apply in this batch (default: 12)")
    parser.add_argument("--stats", action="store_true", help="Show current application stats")
    parser.add_argument("--test-email", action="store_true", help="Send a test notification email")
    parser.add_argument("--schedule", action="store_true", help="Run in daily background scheduler mode")

    args = parser.parse_args()
    print_banner()

    if args.stats:
        run_stats()
    elif args.test_email:
        test_email()
    elif args.schedule:
        schedule_hourly_agent()
    elif args.apply or len(sys.argv) == 1:
        # Default behavior: run hourly batch
        job_applier.run_hourly_application_batch()
        run_stats()

if __name__ == "__main__":
    main()
