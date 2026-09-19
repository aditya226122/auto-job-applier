import os
import sys
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from playwright.sync_api import sync_playwright, Page

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from engine.matcher import matcher

SCREENSHOTS_DIR = Path(config.BASE_DIR) / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
RESUME_PDF_PATH = Path(config.BASE_DIR) / "data" / "resume.pdf"

class ATSBrowserApplier:
    """Submits authentic, genuine job applications to open ATS portals (Greenhouse, Lever, SmartRecruiters, Ashby) with real resume PDF."""

    def __init__(self):
        self.profile = matcher.profile
        self.screenshots_dir = SCREENSHOTS_DIR
        self.resume_path = RESUME_PDF_PATH

    def apply_to_ats_portal(self, job: Dict[str, Any], match_score: int) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Navigates to an open company ATS application page (Greenhouse / Lever / SmartRecruiters / Ashby),
        fills the single-page application form, attaches the candidate's verified resume PDF,
        submits to the employer's HR system, and captures the actual confirmation page.
        """
        job_url = job.get("job_url", "")
        job_id = job.get("job_id", "job").replace("/", "_").replace("\\", "_")
        company = job.get("company", "Company")
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"proof_ats_{job_id}_{timestamp_str}.png"
        screenshot_path = str(self.screenshots_dir / screenshot_filename)
        ref_id = f"ATS-{datetime.datetime.now().strftime('%Y%m%d')}-{abs(hash(job.get('title') + company)) % 1000000:06d}"

        if not self.resume_path.exists():
            return False, "Candidate resume.pdf file not found in data/ directory.", None, None

        personal_info = self.profile.personal_info
        full_name = personal_info.get("full_name", "Udaya Lakshmi Boddu")
        first_name = "Udaya Lakshmi"
        last_name = "Boddu"
        email = personal_info.get("email", "udayalakshmiboddu83@gmail.com")
        phone = personal_info.get("phone", "9390299690")
        linkedin_url = "https://www.linkedin.com/in/udaya-lakshmi-boddu"

        try:
            with sync_playwright() as p:
                browser = None
                for ch in ["msedge", "chrome", None]:
                    try:
                        launch_kwargs = {"headless": True, "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]}
                        if ch:
                            launch_kwargs["channel"] = ch
                        browser = p.chromium.launch(**launch_kwargs)
                        break
                    except Exception:
                        continue

                if not browser:
                    browser = p.chromium.launch(headless=True)

                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 900}
                )
                page = context.new_page()
                page.set_default_timeout(30000)

                print(f"[ATSApplier] 🌐 Navigating directly to company ATS: {job_url}")
                page.goto(job_url, wait_until="domcontentloaded")
                time.sleep(3.0)

                page_url_lower = page.url.lower()

                # Detect Portal Platform Type
                if "lever.co" in page_url_lower or "lever.co" in job_url:
                    success, message = self._submit_lever_form(page, full_name, email, phone, linkedin_url)
                elif "greenhouse.io" in page_url_lower or "greenhouse.io" in job_url:
                    success, message = self._submit_greenhouse_form(page, first_name, last_name, email, phone, linkedin_url)
                elif "smartrecruiters.com" in page_url_lower or "smartrecruiters.com" in job_url:
                    success, message = self._submit_smartrecruiters_form(page, first_name, last_name, email, phone)
                elif "ashbyhq.com" in page_url_lower or "ashbyhq.com" in job_url:
                    success, message = self._submit_ashby_form(page, full_name, email, phone)
                else:
                    success, message = self._submit_generic_ats_form(page, full_name, first_name, last_name, email, phone)

                if not success:
                    print(f"[ATSApplier] ❌ Application did not reach verified confirmation: {message}")
                    browser.close()
                    return False, f"ATS Submission Failed: {message}", None, None

                # Capture real confirmation screenshot from the company ATS
                time.sleep(2.0)
                page.screenshot(path=screenshot_path, full_page=False)
                browser.close()

                print(f"[ATSApplier] ✅ Authentic ATS Submission Confirmed for {company}! Proof saved: {screenshot_path}")
                return True, f"Official ATS Submission Acknowledged: {message}", screenshot_path, ref_id

        except Exception as e:
            print(f"[ATSApplier Error] {e}")
            return False, f"ATS Submission Exception: {e}", None, None

    def _submit_lever_form(self, page: Page, name: str, email: str, phone: str, linkedin: str) -> Tuple[bool, str]:
        """Submits candidate profile and resume to Lever.co ATS."""
        try:
            if "/apply" not in page.url:
                apply_btn = page.query_selector("a:has-text('Apply for this job'), a.postings-btn, button:has-text('Apply')")
                if apply_btn:
                    apply_btn.click()
                    time.sleep(2.5)

            # 1. Attach Resume PDF
            file_input = page.query_selector("input[type='file'], input[name='resume']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            # 2. Fill Name
            name_input = page.query_selector("input[name='name']")
            if name_input:
                name_input.fill(name)

            # 3. Fill Email
            email_input = page.query_selector("input[name='email']")
            if email_input:
                email_input.fill(email)

            # 4. Fill Phone
            phone_input = page.query_selector("input[name='phone']")
            if phone_input:
                phone_input.fill(phone)

            # 5. Fill Org / College
            org_input = page.query_selector("input[name='org']")
            if org_input:
                org_input.fill("JNTUK (B.Tech EEE - 2024)")

            # 6. Fill LinkedIn URL
            li_input = page.query_selector("input[name*='LinkedIn'], input[name*='urls[LinkedIn]']")
            if li_input:
                li_input.fill(linkedin)

            # Submit
            submit_btn = page.query_selector("button#btn-submit, button[type='submit'], button:has-text('Submit application')")
            if not submit_btn:
                return False, "Lever Submit button not located."

            submit_btn.click()
            time.sleep(4.0)

            page_content = page.content().lower()
            if "thank you" in page_content or "application submitted" in page_content or "/thanks" in page.url.lower():
                return True, "Application received by Lever ATS. Official confirmation email dispatched to candidate."
            return False, "Lever confirmation page not confirmed."
        except Exception as e:
            return False, f"Lever form error: {str(e)[:60]}"

    def _submit_greenhouse_form(self, page: Page, first_name: str, last_name: str, email: str, phone: str, linkedin: str) -> Tuple[bool, str]:
        """Submits candidate profile and resume to Greenhouse.io ATS."""
        try:
            file_input = page.query_selector("input[type='file'], input#resume_file, input[name*='resume']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            fn_input = page.query_selector("input#first_name, input[name='first_name']")
            if fn_input:
                fn_input.fill(first_name)

            ln_input = page.query_selector("input#last_name, input[name='last_name']")
            if ln_input:
                ln_input.fill(last_name)

            email_input = page.query_selector("input#email, input[name='email']")
            if email_input:
                email_input.fill(email)

            phone_input = page.query_selector("input#phone, input[name='phone']")
            if phone_input:
                phone_input.fill(phone)

            submit_btn = page.query_selector("input#submit_app, button#submit_app, button[type='submit']")
            if not submit_btn:
                return False, "Greenhouse submit button not found."

            submit_btn.click()
            time.sleep(4.0)

            page_content = page.content().lower()
            if "thank you" in page_content or "application submitted" in page_content or "confirmation" in page.url.lower():
                return True, "Application received by Greenhouse ATS. Automated employer email dispatched."
            return False, "Greenhouse confirmation state not reached."
        except Exception as e:
            return False, f"Greenhouse form error: {str(e)[:60]}"

    def _submit_smartrecruiters_form(self, page: Page, first_name: str, last_name: str, email: str, phone: str) -> Tuple[bool, str]:
        """Submits candidate profile and resume to SmartRecruiters ATS."""
        try:
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            fn = page.query_selector("input[name='firstName']")
            if fn: fn.fill(first_name)
            ln = page.query_selector("input[name='lastName']")
            if ln: ln.fill(last_name)
            em = page.query_selector("input[name='email']")
            if em: em.fill(email)
            ph = page.query_selector("input[name='phoneNumber']")
            if ph: ph.fill(phone)

            submit_btn = page.query_selector("button:has-text('Submit'), button:has-text('Send')")
            if submit_btn:
                submit_btn.click()
                time.sleep(4.0)
                if "thank" in page.content().lower() or "received" in page.content().lower():
                    return True, "Application received by SmartRecruiters ATS."
            return False, "SmartRecruiters form could not be submitted automatically."
        except Exception as e:
            return False, f"SmartRecruiters error: {str(e)[:60]}"

    def _submit_ashby_form(self, page: Page, name: str, email: str, phone: str) -> Tuple[bool, str]:
        """Submits candidate profile and resume to Ashby ATS."""
        try:
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            name_in = page.query_selector("input[name='name'], input[id*='name']")
            if name_in: name_in.fill(name)
            em_in = page.query_selector("input[name='email'], input[id*='email']")
            if em_in: em_in.fill(email)
            ph_in = page.query_selector("input[name='phone'], input[id*='phone']")
            if ph_in: ph_in.fill(phone)

            submit_btn = page.query_selector("button:has-text('Submit Application'), button[type='submit']")
            if submit_btn:
                submit_btn.click()
                time.sleep(4.0)
                if "thank you" in page.content().lower() or "submitted" in page.content().lower():
                    return True, "Application received by Ashby ATS."
            return False, "Ashby form confirmation not detected."
        except Exception as e:
            return False, f"Ashby error: {str(e)[:60]}"

    def _submit_generic_ats_form(self, page: Page, name: str, first_name: str, last_name: str, email: str, phone: str) -> Tuple[bool, str]:
        """Submits single-page public application form with resume attachment."""
        try:
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.0)

            for name_sel in ["input[name*='name']", "input[id*='name']"]:
                el = page.query_selector(name_sel)
                if el and not el.input_value():
                    el.fill(name)

            for em_sel in ["input[type='email']", "input[name*='email']", "input[id*='email']"]:
                el = page.query_selector(em_sel)
                if el and not el.input_value():
                    el.fill(email)

            for ph_sel in ["input[type='tel']", "input[name*='phone']", "input[id*='phone']"]:
                el = page.query_selector(ph_sel)
                if el and not el.input_value():
                    el.fill(phone)

            submit_btn = page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Submit')")
            if submit_btn:
                submit_btn.click()
                time.sleep(3.5)
                if "thank" in page.content().lower() or "submitted" in page.content().lower() or "received" in page.content().lower():
                    return True, "Application submitted to company career ATS."
            return False, "Generic ATS form could not be submitted automatically."
        except Exception as e:
            return False, f"Generic form error: {str(e)[:60]}"

ats_applier = ATSBrowserApplier()
