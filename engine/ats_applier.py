import os
import sys
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from playwright.sync_api import sync_playwright, Page

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from engine.matcher import matcher
from engine.verifier import verifier

SCREENSHOTS_DIR = Path(config.BASE_DIR) / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
RESUME_PDF_PATH = Path(config.BASE_DIR) / "data" / "resume.pdf"

class ATSBrowserApplier:
    """Automates genuine job applications to ATS portals (Greenhouse, Lever, SmartRecruiters, Ashby, Workable) with real candidate resume and data."""

    def __init__(self):
        self.profile = matcher.profile
        self.resume_path = RESUME_PDF_PATH

    def apply_to_ats_portal(self, job: Dict[str, Any], match_score: int) -> Tuple[bool, str, Optional[str], Optional[str]]:
        job_url = job.get("job_url", "")
        company = job.get("company", "Company")

        if not self.resume_path.exists():
            return False, "Candidate resume.pdf file not found in data/ directory.", None, None

        personal_info = self.profile.personal_info
        full_name = personal_info.get("full_name", "Udaya Lakshmi Boddu")
        first_name = "Udaya Lakshmi"
        last_name = "Boddu"
        email = personal_info.get("email", "udayalakshmiboddu83@gmail.com")
        phone = personal_info.get("phone", "9390299690")
        location = personal_info.get("location", "Visakhapatnam, Andhra Pradesh, India")
        linkedin = personal_info.get("linkedin", "https://www.linkedin.com/in/udaya-lakshmi-boddu")
        github = personal_info.get("github", "https://github.com/udayalakshmiboddu")

        try:
            with sync_playwright() as p:
                browser = None
                for ch in ["msedge", "chrome", None]:
                    try:
                        launch_kwargs = {
                            "headless": True,
                            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                        }
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
                page.set_default_timeout(35000)

                print(f"[ATSApplier] 🌐 Navigating to verified ATS job URL: {job_url}")
                page.goto(job_url, wait_until="domcontentloaded")
                time.sleep(3.0)

                page_url_lower = page.url.lower()

                # Dispatch to specific ATS form filler
                if "lever.co" in page_url_lower or "lever.co" in job_url.lower():
                    submitted = self._submit_lever(page, full_name, email, phone, linkedin)
                elif "greenhouse.io" in page_url_lower or "greenhouse.io" in job_url.lower():
                    submitted = self._submit_greenhouse(page, first_name, last_name, email, phone, linkedin, location)
                elif "smartrecruiters.com" in page_url_lower or "smartrecruiters.com" in job_url.lower():
                    submitted = self._submit_smartrecruiters(page, first_name, last_name, email, phone, location)
                elif "ashbyhq.com" in page_url_lower or "ashbyhq.com" in job_url.lower():
                    submitted = self._submit_ashby(page, full_name, email, phone, linkedin)
                else:
                    submitted = self._submit_generic_ats(page, full_name, first_name, last_name, email, phone, location)

                if not submitted:
                    print(f"[ATSApplier] ❌ Form submission action could not complete.")
                    browser.close()
                    return False, "Could not fill or submit the application form.", None, None

                # Wait for post-submission transition
                time.sleep(4.0)

                # Strict Confirmation Verification
                is_confirmed, conf_msg, screenshot_path, ref_id = verifier.verify_page_submission(
                    page=page,
                    job=job,
                    candidate_info=personal_info
                )

                browser.close()

                if is_confirmed:
                    print(f"[ATSApplier] ✅ 100% Verified Application Confirmed: {conf_msg}")
                    return True, conf_msg, screenshot_path, ref_id
                else:
                    print(f"[ATSApplier] ❌ Confirmation failed: {conf_msg}")
                    return False, f"Submission not verified: {conf_msg}", None, None

        except Exception as e:
            print(f"[ATSApplier Exception] {e}")
            return False, f"ATS automation error: {str(e)[:80]}", None, None

    def _submit_lever(self, page: Page, name: str, email: str, phone: str, linkedin: str) -> bool:
        try:
            if "/apply" not in page.url:
                apply_btn = page.query_selector("a:has-text('Apply for this job'), a.postings-btn, button:has-text('Apply')")
                if apply_btn:
                    apply_btn.click()
                    time.sleep(2.0)

            # Attach Resume
            file_input = page.query_selector("input[type='file'], input[name='resume']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            # Fill Fields
            self._fill_if_present(page, "input[name='name']", name)
            self._fill_if_present(page, "input[name='email']", email)
            self._fill_if_present(page, "input[name='phone']", phone)
            self._fill_if_present(page, "input[name='org']", "JNTUK (B.Tech EEE - 2024, CGPA 7.4)")
            self._fill_if_present(page, "input[name*='urls[LinkedIn]']", linkedin)

            # Check Consent Checkboxes
            for cb in page.query_selector_all("input[type='checkbox']"):
                try:
                    if not cb.is_checked():
                        cb.check()
                except Exception:
                    pass

            # Submit
            submit_btn = page.query_selector("button#btn-submit, button[type='submit'], button:has-text('Submit application')")
            if submit_btn:
                submit_btn.click()
                return True
            return False
        except Exception:
            return False

    def _submit_greenhouse(self, page: Page, first_name: str, last_name: str, email: str, phone: str, linkedin: str, location: str) -> bool:
        try:
            # Attach Resume
            file_input = page.query_selector("input[type='file'], input#resume_file, input[name*='resume']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            self._fill_if_present(page, "input#first_name, input[name='first_name']", first_name)
            self._fill_if_present(page, "input#last_name, input[name='last_name']", last_name)
            self._fill_if_present(page, "input#email, input[name='email']", email)
            self._fill_if_present(page, "input#phone, input[name='phone']", phone)

            # Optional/Custom fields
            for inp in page.query_selector_all("input[id*='job_application_answers_attributes']"):
                try:
                    label = page.inner_text(f"label[for='{inp.get_attribute('id')}']").lower()
                    if "linkedin" in label and not inp.input_value():
                        inp.fill(linkedin)
                    elif "website" in label or "portfolio" in label or "github" in label:
                        inp.fill("https://github.com/udayalakshmiboddu")
                except Exception:
                    pass

            # Check Consent Checkboxes
            for cb in page.query_selector_all("input[type='checkbox']"):
                try:
                    if not cb.is_checked():
                        cb.check()
                except Exception:
                    pass

            # Submit
            submit_btn = page.query_selector("input#submit_app, button#submit_app, button[type='submit'], input[type='submit']")
            if submit_btn:
                submit_btn.click()
                return True
            return False
        except Exception:
            return False

    def _submit_smartrecruiters(self, page: Page, first_name: str, last_name: str, email: str, phone: str, location: str) -> bool:
        try:
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            self._fill_if_present(page, "input[name='firstName'], input#first-name-input", first_name)
            self._fill_if_present(page, "input[name='lastName'], input#last-name-input", last_name)
            self._fill_if_present(page, "input[name='email'], input#email-input", email)
            self._fill_if_present(page, "input[name='phoneNumber'], input#phone-number-input", phone)
            self._fill_if_present(page, "input[name='city'], input#city-input", "Visakhapatnam")

            submit_btn = page.query_selector("button:has-text('Submit'), button:has-text('Send'), button[type='submit']")
            if submit_btn:
                submit_btn.click()
                return True
            return False
        except Exception:
            return False

    def _submit_ashby(self, page: Page, name: str, email: str, phone: str, linkedin: str) -> bool:
        try:
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            self._fill_if_present(page, "input[name='name'], input[id*='name']", name)
            self._fill_if_present(page, "input[name='email'], input[id*='email']", email)
            self._fill_if_present(page, "input[name='phone'], input[id*='phone']", phone)

            submit_btn = page.query_selector("button:has-text('Submit Application'), button[type='submit']")
            if submit_btn:
                submit_btn.click()
                return True
            return False
        except Exception:
            return False

    def _submit_generic_ats(self, page: Page, name: str, first_name: str, last_name: str, email: str, phone: str, location: str) -> bool:
        try:
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.5)

            for sel, val in [
                ("input[name*='first_name'], input[id*='first_name']", first_name),
                ("input[name*='last_name'], input[id*='last_name']", last_name),
                ("input[name*='name'], input[id*='name'], input[placeholder*='Name']", name),
                ("input[type='email'], input[name*='email'], input[id*='email']", email),
                ("input[type='tel'], input[name*='phone'], input[id*='phone'], input[name*='mobile']", phone),
                ("input[name*='location'], input[name*='city'], input[placeholder*='City']", "Visakhapatnam, India")
            ]:
                self._fill_if_present(page, sel, val)

            # Check required checkboxes
            for cb in page.query_selector_all("input[type='checkbox']"):
                try:
                    if not cb.is_checked():
                        cb.check()
                except Exception:
                    pass

            submit_btn = page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Submit Application'), button:has-text('Apply')")
            if submit_btn:
                submit_btn.click()
                return True
            return False
        except Exception:
            return False

    def _fill_if_present(self, page: Page, selector: str, value: str):
        try:
            el = page.query_selector(selector)
            if el and not el.input_value():
                el.fill(value)
        except Exception:
            pass

ats_applier = ATSBrowserApplier()
