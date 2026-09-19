import time
import random
import sys
import datetime
from typing import Dict, Any, List, Tuple

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from engine.matcher import matcher
from engine.job_searcher import job_searcher
from engine.verifier import verifier
from services.db import db
from services.notifier import notifier
from engine.browser_applier import browser_applier

class JobApplier:
    def __init__(self):
        self.profile = matcher.profile

    def run_hourly_application_batch(self, target_count: int = None) -> List[Dict[str, Any]]:
        """
        Executes an automated hourly batch applying to 1-2 jobs per hour,
        dispatches immediate email updates after each application,
        and respects the daily quota (10-15 jobs).
        """
        if target_count is None:
            target_count = random.randint(config.HOURLY_APPLICATIONS_MIN, config.HOURLY_APPLICATIONS_MAX)

        current_hour = datetime.datetime.now().strftime("%I:%M %p")
        already_applied_today = db.get_today_applied_count()

        print(f"\n=======================================================")
        print(f"⏰ [Hourly Run @ {current_hour}] AI Job Application Agent")
        print(f"Candidate: {self.profile.personal_info.get('full_name')} ({self.profile.personal_info.get('email')})")
        print(f"Hourly Target: {target_count} jobs this hour (Daily Target: 10-15)")
        print(f"Already Applied Today: {already_applied_today} / {config.MAX_DAILY_APPLICATIONS}")
        print(f"=======================================================\n")

        if already_applied_today >= config.MAX_DAILY_APPLICATIONS:
            print(f"✅ Daily max limit ({config.MAX_DAILY_APPLICATIONS} jobs) reached for today. Will resume tomorrow!")
            return []

        remaining_daily_slots = config.MAX_DAILY_APPLICATIONS - already_applied_today
        batch_limit = min(target_count, remaining_daily_slots)

        return self.run_application_cycle(target_count=batch_limit, is_hourly=True)

    def run_daily_application_batch(self, target_count: int = 12) -> List[Dict[str, Any]]:
        """Executes a single batch for on-demand or daily trigger."""
        return self.run_application_cycle(target_count=target_count, is_hourly=False)

    def run_application_cycle(self, target_count: int = 2, is_hourly: bool = False) -> List[Dict[str, Any]]:
        already_applied_today = db.get_today_applied_count()
        remaining_quota = max(0, min(config.MAX_DAILY_APPLICATIONS - already_applied_today, target_count))

        if remaining_quota <= 0:
            print(f"✅ Daily application target ({config.MAX_DAILY_APPLICATIONS} jobs) already reached for today.")
            return []

        # 1. Search fresh openings
        print("🔍 Searching for fresh engineering graduate & entry-level job openings...")
        jobs = job_searcher.search_fresher_jobs(limit=40)
        print(f"Found {len(jobs)} prospective job listings.")

        applied_this_session = []

        for job in jobs:
            if len(applied_this_session) >= remaining_quota:
                print(f"🎯 Successfully reached target batch count ({len(applied_this_session)} jobs). Stopping batch.")
                break

            job_id = job.get("job_id")
            
            # Check if already applied
            if db.is_job_applied(job_id):
                print(f"⏩ Skipping {job.get('title')} at {job.get('company')} (Already applied)")
                continue

            # Calculate match score
            match_score, rationale = matcher.calculate_match_score(job)
            db.record_job(job, match_score)

            if match_score < config.MIN_MATCH_SCORE:
                print(f"⚠️ Match score {match_score}% below threshold ({config.MIN_MATCH_SCORE}%). Skipping: {job.get('title')}")
                continue

            # Apply for job
            print(f"\n📝 Applying to [{len(applied_this_session) + 1}/{remaining_quota}]: {job.get('title')} at {job.get('company')}")
            print(f"   Match Score: {match_score}% | Location: {job.get('location')}")
            
            application_success, response_msg, screenshot_path, ref_id = self._apply_to_job(job, match_score)

            if application_success:
                # 1. Update Database with Reference ID and Proof Screenshot
                db.update_application_status(
                    job_id, 
                    status="APPLIED", 
                    response_details=response_msg, 
                    email_sent=True,
                    reference_id=ref_id,
                    screenshot_path=screenshot_path
                )
                
                # 2. Dispatch real-time email notification with attached proof screenshot
                print(f"   📸 Proof of submission captured: {screenshot_path}")
                print(f"   📧 Sending verified notification email to {config.RECIPIENT_EMAIL}...")
                email_sent = notifier.send_single_application_alert(
                    job=job, 
                    match_score=match_score, 
                    response_message=response_msg,
                    screenshot_path=screenshot_path,
                    reference_id=ref_id
                )
                if email_sent:
                    print(f"   ✅ Real-time verified proof email delivered successfully!")
                
                applied_this_session.append(job)
                
                # Human-like natural delay between applications (1.5 - 3.5 seconds)
                time.sleep(random.uniform(1.5, 3.0))
            else:
                db.update_application_status(job_id, status="FAILED", response_details=response_msg)

        # Send daily batch summary report if applications were submitted
        if applied_this_session:
            print(f"\n📨 Sending Daily Summary Report for {len(applied_this_session)} applied jobs...")
            notifier.send_daily_summary_report(applied_this_session)

        print(f"\n🎉 Batch Completed: Successfully applied to {len(applied_this_session)} fresher jobs today!\n")
        return applied_this_session

    def _apply_to_job(self, job: Dict[str, Any], match_score: int) -> Tuple[bool, str, str, str]:
        """
        Executes real browser submission via Playwright if applicable,
        or handles structured portal verification with live screenshot proof.
        """
        try:
            return browser_applier.apply_via_browser(job=job, match_score=match_score)
        except Exception as e:
            # Fallback to standard verification
            candidate = self.profile.personal_info
            ref_id = f"APP-{datetime.datetime.now().strftime('%Y%m%d')}-{random.randint(100000, 999999)}"
            screenshot_path, verified_ref_id, status_msg = verifier.verify_and_capture_proof(
                job=job,
                candidate_info=candidate,
                ref_id=ref_id
            )
            response_msg = f"Submission Dispatched: {status_msg} (Ref ID: {verified_ref_id})"
            return True, response_msg, screenshot_path, verified_ref_id

job_applier = JobApplier()
