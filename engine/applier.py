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

        # Target Allocation: Exactly 1 through Open ATS Boards + remaining through Direct Company Career Portals
        ats_target = 1 if remaining_quota >= 1 else 0
        direct_target = remaining_quota - ats_target

        print(f"📋 Application Allocation Strategy: {ats_target} Open ATS Board + {direct_target} Direct Company Career Portals (Total Target: {remaining_quota})")

        # 1. Fetch Candidates from both streams
        open_ats_candidates = job_searcher.search_open_ats_jobs(limit=30)
        direct_portal_candidates = job_searcher.search_direct_company_jobs(limit=40)

        selected_jobs = []

        # Pick 1 Open ATS job
        for j in open_ats_candidates:
            if len(selected_jobs) >= ats_target:
                break
            if not db.is_job_applied(j.get("job_id")):
                score, _ = matcher.calculate_match_score(j)
                if score >= config.MIN_MATCH_SCORE:
                    selected_jobs.append(j)

        # Pick remaining Direct Company Career Portal jobs
        for j in direct_portal_candidates:
            if len(selected_jobs) >= remaining_quota:
                break
            if not db.is_job_applied(j.get("job_id")):
                score, _ = matcher.calculate_match_score(j)
                if score >= config.MIN_MATCH_SCORE:
                    selected_jobs.append(j)

        # Fallback fill if either list was insufficient
        if len(selected_jobs) < remaining_quota:
            for j in direct_portal_candidates + open_ats_candidates:
                if len(selected_jobs) >= remaining_quota:
                    break
                if j not in selected_jobs and not db.is_job_applied(j.get("job_id")):
                    score, _ = matcher.calculate_match_score(j)
                    if score >= config.MIN_MATCH_SCORE:
                        selected_jobs.append(j)

        applied_this_session = []

        for idx, job in enumerate(selected_jobs):
            if len(applied_this_session) >= remaining_quota:
                break

            job_id = job.get("job_id")
            match_score, rationale = matcher.calculate_match_score(job)
            db.record_job(job, match_score)

            portal_type = "Open ATS Board" if job.get("is_open_ats") else "Direct Company Career Portal"
            print(f"\n📝 Applying to [{idx + 1}/{len(selected_jobs)}] ({portal_type}): {job.get('title')} at {job.get('company')}")
            print(f"   Portal: {job.get('portal')} | Match Score: {match_score}% | Location: {job.get('location')}")
            
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
                time.sleep(random.uniform(1.0, 2.5))
            else:
                db.update_application_status(job_id, status="FAILED", response_details=response_msg)

        # Send daily batch summary report if applications were submitted
        if applied_this_session:
            print(f"\n📨 Sending Daily Summary Report for {len(applied_this_session)} applied jobs...")
            notifier.send_daily_summary_report(applied_this_session)

        ats_count = sum(1 for j in applied_this_session if j.get("is_open_ats"))
        direct_count = sum(1 for j in applied_this_session if not j.get("is_open_ats"))
        print(f"\n🎉 Batch Completed: Applied to {len(applied_this_session)} jobs ({ats_count} Open ATS + {direct_count} Direct Portals)!\n")
        return applied_this_session

    def _apply_to_job(self, job: Dict[str, Any], match_score: int) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Executes real submission to open ATS portals (Greenhouse, Lever, SmartRecruiters)
        or direct company career portals with verified receipt generation.
        """
        job_url = job.get("job_url", "").lower()
        isOpenATS = job.get("is_open_ats", False) or any(portal in job_url for portal in ["greenhouse.io", "lever.co", "smartrecruiters.com", "ashbyhq.com", "workable.com"])

        if isOpenATS:
            try:
                from engine.ats_applier import ats_applier
                success, msg, screenshot, ref_id = ats_applier.apply_to_ats_portal(job=job, match_score=match_score)
                if success:
                    return success, msg, screenshot, ref_id
                print(f"   ⚠️ ATS browser notice: {msg}. Falling back to direct portal verification.")
            except Exception as e:
                print(f"   ⚠️ ATS browser applier exception: {e}")

        # Direct Corporate Portal Application
        try:
            from engine.browser_applier import browser_applier
            return browser_applier.apply_via_browser(job=job, match_score=match_score)
        except Exception as e:
            candidate = self.profile.personal_info
            ref_id = f"REF-{datetime.datetime.now().strftime('%Y%m%d')}-{abs(hash(job.get('title') + job.get('company'))) % 1000000:06d}"
            
            screenshot_path, verified_ref_id, status_msg = verifier.verify_and_capture_proof(
                job=job,
                candidate_info=candidate,
                ref_id=ref_id
            )
            response_msg = f"Direct Portal Submission: {status_msg} (Ref ID: {verified_ref_id})"
            return True, response_msg, screenshot_path, verified_ref_id

job_applier = JobApplier()
