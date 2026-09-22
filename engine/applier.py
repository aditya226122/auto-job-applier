import time
import random
import sys
import datetime
from typing import Dict, Any, List, Tuple, Optional

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from engine.matcher import matcher
from engine.job_searcher import job_searcher
from services.db import db
from services.notifier import notifier

class JobApplier:
    def __init__(self):
        self.profile = matcher.profile

    def run_hourly_application_batch(self, target_count: int = None) -> List[Dict[str, Any]]:
        """
        Executes an automated hourly batch applying to 1-2 jobs per hour,
        strictly verifying confirmation before marking applied and dispatching proof emails.
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

        # Target Allocation: 1 Open ATS Board + remaining Direct Company Career Portals
        ats_target = 1 if remaining_quota >= 1 else 0
        direct_target = remaining_quota - ats_target

        print(f"📋 Application Strategy: {ats_target} Open ATS + {direct_target} Direct Portals (Target: {remaining_quota})")

        # 1. Fetch Candidates from both streams
        open_ats_candidates = job_searcher.search_open_ats_jobs(limit=40)
        direct_portal_candidates = job_searcher.search_direct_company_jobs(limit=40)

        candidate_pool = []

        # Prioritize Open ATS candidates with match score >= threshold
        for j in open_ats_candidates:
            if not db.is_job_applied(j.get("job_id")):
                score, _ = matcher.calculate_match_score(j)
                if score >= config.MIN_MATCH_SCORE:
                    candidate_pool.append((j, score))

        # Add Direct Portal candidates
        for j in direct_portal_candidates:
            if not db.is_job_applied(j.get("job_id")):
                score, _ = matcher.calculate_match_score(j)
                if score >= config.MIN_MATCH_SCORE:
                    candidate_pool.append((j, score))

        applied_this_session = []

        for idx, (job, match_score) in enumerate(candidate_pool):
            if len(applied_this_session) >= remaining_quota:
                break

            job_id = job.get("job_id")
            db.record_job(job, match_score)

            portal_type = "Open ATS Board" if job.get("is_open_ats") else "Direct Company Career Portal"
            print(f"\n📝 [{len(applied_this_session) + 1}/{remaining_quota}] Processing {job.get('title')} at {job.get('company')} ({portal_type})")
            print(f"   URL: {job.get('job_url')} | Match Score: {match_score}%")
            
            application_success, response_msg, screenshot_path, ref_id = self._apply_to_job(job, match_score)

            if application_success and screenshot_path:
                # 1. Record authentic application in database
                db.update_application_status(
                    job_id, 
                    status="APPLIED", 
                    response_details=response_msg, 
                    email_sent=True,
                    reference_id=ref_id,
                    screenshot_path=screenshot_path
                )
                
                # 2. Dispatch verified email alert with authentic post-submission proof screenshot
                print(f"   📸 Genuine proof captured: {screenshot_path}")
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
                time.sleep(random.uniform(2.0, 4.0))
            else:
                # Mark as FAILED or UNVERIFIED - DO NOT SEND SUCCESS EMAIL
                print(f"   ❌ Application unconfirmed: {response_msg}. Marked as FAILED (No email sent).")
                db.update_application_status(job_id, status="FAILED", response_details=response_msg)

        # Send summary report only if applications were actually submitted
        if applied_this_session:
            print(f"\n📨 Sending Summary Report for {len(applied_this_session)} verified applications...")
            notifier.send_daily_summary_report(applied_this_session)

        print(f"\n🎉 Session Finished: Successfully verified & applied to {len(applied_this_session)} jobs!\n")
        return applied_this_session

    def _apply_to_job(self, job: Dict[str, Any], match_score: int) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Executes real browser submission to ATS or Company Portal with strict verification.
        Returns ONLY (True, ...) if the submission actually succeeded and reached confirmation.
        """
        job_url = job.get("job_url", "").lower()
        isOpenATS = job.get("is_open_ats", False) or any(p in job_url for p in ["greenhouse.io", "lever.co", "smartrecruiters.com", "ashbyhq.com", "workable.com"])

        if isOpenATS:
            try:
                from engine.ats_applier import ats_applier
                return ats_applier.apply_to_ats_portal(job=job, match_score=match_score)
            except Exception as e:
                print(f"   ⚠️ ATS applier exception: {e}")
                return False, f"ATS applier error: {e}", None, None

        # Direct Corporate Portal Application
        try:
            from engine.browser_applier import browser_applier
            return browser_applier.apply_via_browser(job=job, match_score=match_score)
        except Exception as e:
            print(f"   ⚠️ Browser applier exception: {e}")
            return False, f"Direct portal applier error: {e}", None, None

job_applier = JobApplier()
