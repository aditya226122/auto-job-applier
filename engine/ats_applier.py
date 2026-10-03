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
                            "args": [
                                "--no-sandbox",
                                "--disable-setuid-sandbox",
                                "--disable-dev-shm-usage",
                                "--ignore-certificate-errors",
                                "--disable-blink-features=AutomationControlled"
                            ]
                        }
                        if ch:
                            launch_kwargs["channel"] = ch
                        browser = p.chromium.launch(**launch_kwargs)
                        break
                    except Exception:
                        continue

                if not browser:
                    browser = p.chromium.launch(headless=True, channel="msedge")

                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 900},
                    ignore_https_errors=True
                )
                page = context.new_page()
                page.set_default_timeout(35000)

                print(f"[ATSApplier] 🌐 Navigating to verified ATS job URL: {job_url}")
                page.goto(job_url, wait_until="domcontentloaded")
                time.sleep(2.5)

                page_url_lower = page.url.lower()

                # Dispatch to specific ATS form filler
                if "lever.co" in page_url_lower or "lever.co" in job_url.lower():
                    submitted = self._submit_lever(page, full_name, email, phone, linkedin)
                elif "greenhouse.io" in page_url_lower or "greenhouse.io" in job_url.lower() or "boards.greenhouse.io" in job_url.lower():
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
                time.sleep(1.0)

            # Fill Core Fields
            self._fill_if_present(page, "input[name='name']", name)
            self._fill_if_present(page, "input[name='email']", email)
            self._fill_if_present(page, "input[name='phone']", phone)
            self._fill_if_present(page, "input[name='org']", "JNTUK (B.Tech EEE - 2024, CGPA 7.4)")
            self._fill_if_present(page, "input[name*='urls[LinkedIn]']", linkedin)
            self._fill_if_present(page, "input[name*='urls[GitHub]']", "https://github.com/udayalakshmiboddu")

            # Custom questions on Lever
            for ctrl in page.query_selector_all("input[type='text'], textarea"):
                try:
                    if ctrl.input_value():
                        continue
                    lbl = (ctrl.get_attribute("name") or "").lower()
                    if "experience" in lbl or "background" in lbl:
                        ctrl.fill("2024 Graduate from JNTUK with practical projects in Embedded Systems, IoT, C programming, and SQL database automation.")
                    elif "notice" in lbl:
                        ctrl.fill("Immediate")
                    elif ctrl.get_attribute("required") is not None:
                        ctrl.fill("Yes")
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
            submit_btn = page.query_selector("button#btn-submit, button[type='submit'], button:has-text('Submit application')")
            if submit_btn:
                submit_btn.click()
                return True
            return False
        except Exception:
            return False

    def _submit_greenhouse(self, page: Page, first_name: str, last_name: str, email: str, phone: str, linkedin: str, location: str) -> bool:
        try:
            # 1. Attach Resume
            file_input = page.query_selector("input[type='file'], input#resume_file, input[name*='resume']")
            if file_input:
                file_input.set_input_files(str(self.resume_path))
                time.sleep(1.0)

            # 2. Base Fields
            self._fill_if_present(page, "input#first_name, input[name='first_name']", first_name)
            self._fill_if_present(page, "input#last_name, input[name='last_name']", last_name)
            self._fill_if_present(page, "input#email, input[name='email']", email)
            self._fill_if_present(page, "input#phone, input[name='phone']", phone)
            self._fill_if_present(page, "input#country, input[name='country']", "India")
            self._fill_if_present(page, "input#school--0, input[name*='school']", "Jawaharlal Nehru Technological University Kakinada (JNTUK)")
            self._fill_if_present(page, "input#degree--0, input[name*='degree']", "Bachelor of Technology - B.Tech")
            self._fill_if_present(page, "input#discipline--0, input[name*='discipline']", "Electrical and Electronics Engineering")

            # 3. Intelligent Custom Question Handler (covers all custom essay/mandatory questions)
            for ctrl in page.query_selector_all("input[type='text'], textarea"):
                try:
                    if ctrl.input_value():
                        continue
                    cid = ctrl.get_attribute("id") or ""
                    cname = ctrl.get_attribute("name") or ""
                    lbl_el = page.query_selector(f"label[for='{cid}']") if cid else None
                    lbl = (lbl_el.inner_text() if lbl_el else cname).lower()

                    if "math" in lbl:
                        ctrl.fill("Top 10% / Grade A in Mathematics")
                    elif "native language" in lbl or "language" in lbl:
                        ctrl.fill("Excellent / Fluent in English and Telugu")
                    elif "degree" in lbl or "gpa" in lbl or "result" in lbl or "bachelor" in lbl:
                        ctrl.fill("B.Tech in Electrical & Electronics Engineering (EEE), JNTUK, 2024 Graduate with CGPA 7.4 / 10")
                    elif "country" in lbl or "work" in lbl or "location" in lbl or "nationality" in lbl:
                        ctrl.fill("India")
                    elif "gender" in lbl:
                        ctrl.fill("Female")
                    elif "race" in lbl or "ethnicity" in lbl:
                        ctrl.fill("Asian / Indian")
                    elif "linkedin" in lbl:
                        ctrl.fill(linkedin)
                    elif "website" in lbl or "github" in lbl or "portfolio" in lbl:
                        ctrl.fill("https://github.com/udayalakshmiboddu")
                    elif "experience" in lbl or "describe" in lbl:
                        ctrl.fill("2024 Engineering Graduate from JNTUK with practical academic project experience in Embedded Systems, IoT, C programming, and SQL data automation.")
                    elif "agree" in lbl or "confirm" in lbl or "meet" in lbl or "travel" in lbl:
                        ctrl.fill("Yes, I agree and confirm.")
                    elif ctrl.get_attribute("required") is not None:
                        ctrl.fill("Yes / Applicable as per graduate engineering profile")
                except Exception:
                    pass

            # 4. Handle custom Greenhouse dropdown / select elements
            for custom_sel in page.query_selector_all("div[class*='select'], div[role='combobox']"):
                try:
                    btn = custom_sel.query_selector("button, div[class*='control']")
                    if btn and ("select" in btn.inner_text().lower() or not btn.inner_text().strip()):
                        btn.click()
                        time.sleep(0.3)
                        opt = page.query_selector("div[role='option'], div[class*='option']")
                        if opt:
                            opt.click()
                except Exception:
                    pass

            # 5. Native <select> elements
            for sel_el in page.query_selector_all("select"):
                try:
                    options = sel_el.query_selector_all("option")
                    if len(options) > 1 and not sel_el.input_value():
                        sel_el.select_option(index=1)
                except Exception:
                    pass

            # 6. Check Consent Checkboxes
            for cb in page.query_selector_all("input[type='checkbox']"):
                try:
                    if not cb.is_checked():
                        cb.check()
                except Exception:
                    pass

            # 7. Submit Application
            submit_btn = page.query_selector("input#submit_app, button#submit_app, button[type='submit'], input[type='submit'], button:has-text('Submit Application')")
            if submit_btn:
                submit_btn.scroll_into_view_if_needed()
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
                time.sleep(1.0)

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
                time.sleep(1.0)

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
                time.sleep(1.0)

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
