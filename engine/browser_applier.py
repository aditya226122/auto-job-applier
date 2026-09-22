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
from engine.otp_handler import otp_handler

SCREENSHOTS_DIR = Path(config.BASE_DIR) / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
RESUME_PDF_PATH = Path(config.BASE_DIR) / "data" / "resume.pdf"

class PlaywrightBrowserApplier:
    """Executes live, authentic browser automation submissions on Direct Company Career Portals."""

    def __init__(self):
        self.profile = matcher.profile
        self.resume_path = RESUME_PDF_PATH

    def apply_via_browser(self, job: Dict[str, Any], match_score: int) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Navigates to direct company job page, detects application form,
        fills candidate details and attaches resume, submits, and strictly verifies confirmation.
        """
        job_url = job.get("job_url", "")
        company = job.get("company", "Company")

        if not self.resume_path.exists():
            return False, "Candidate resume.pdf file not found.", None, None

        personal_info = self.profile.personal_info
        full_name = personal_info.get("full_name", "Udaya Lakshmi Boddu")
        first_name = "Udaya Lakshmi"
        last_name = "Boddu"
        email = personal_info.get("email", "udayalakshmiboddu83@gmail.com")
        phone = personal_info.get("phone", "9390299690")
        portal_password = config.CANDIDATE_PORTAL_PASSWORD or "Udaya@JNTUK2024!"

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

                print(f"[BrowserApplier] 🌐 Navigating to direct corporate portal: {job_url}")
                page.goto(job_url, wait_until="domcontentloaded")
                time.sleep(3.0)

                # 1. Check if on an overview/landing page that requires clicking an Apply button
                apply_button = page.query_selector("a:has-text('Apply Now'), a:has-text('Apply Online'), button:has-text('Apply Now'), button:has-text('Apply Online'), a.apply-btn, a[href*='apply']")
                if apply_button:
                    try:
                        apply_button.click()
                        time.sleep(3.0)
                    except Exception:
                        pass

                # 2. Check for Candidate Account Login / Registration form
                email_input = page.query_selector("input[type='email'], input[name*='email'], input[id*='email']")
                pwd_input = page.query_selector("input[type='password'], input[name*='password']")
                
                if email_input and pwd_input:
                    try:
                        email_input.fill(email)
                        pwd_input.fill(portal_password)
                        
                        # Sign up / Log in button
                        login_btn = page.query_selector("button:has-text('Sign In'), button:has-text('Log In'), button:has-text('Create Account'), button:has-text('Register')")
                        if login_btn:
                            login_btn.click()
                            time.sleep(3.0)

                            # Check for OTP verification
                            otp_input = page.query_selector("input[name*='otp'], input[name*='code'], input[placeholder*='OTP'], input[placeholder*='Verification']")
                            if otp_input:
                                print(f"[BrowserApplier] 🔑 OTP input detected on portal. Polling candidate inbox for code...")
                                otp_code = otp_handler.wait_for_otp(sender_hint=company, timeout_seconds=45)
                                if otp_code:
                                    otp_input.fill(otp_code)
                                    verify_btn = page.query_selector("button:has-text('Verify'), button:has-text('Submit Code')")
                                    if verify_btn:
                                        verify_btn.click()
                                        time.sleep(3.0)
                    except Exception as e:
                        print(f"[BrowserApplier] Portal auth error: {e}")

                # 3. Fill Application Form
                file_input = page.query_selector("input[type='file']")
                if file_input:
                    try:
                        file_input.set_input_files(str(self.resume_path))
                        time.sleep(1.5)
                    except Exception:
                        pass

                for sel, val in [
                    ("input[name*='first_name'], input[id*='first_name'], input[name*='firstName']", first_name),
                    ("input[name*='last_name'], input[id*='last_name'], input[name*='lastName']", last_name),
                    ("input[name*='name'], input[id*='name'], input[placeholder*='Full Name']", full_name),
                    ("input[type='email'], input[name*='email'], input[id*='email']", email),
                    ("input[type='tel'], input[name*='phone'], input[id*='phone'], input[name*='mobile']", phone),
                    ("input[name*='experience'], input[id*='experience']", "0"),
                    ("input[name*='notice'], input[id*='notice']", "Immediate"),
                    ("input[name*='location'], input[id*='location']", "Visakhapatnam, Andhra Pradesh, India")
                ]:
                    try:
                        el = page.query_selector(sel)
                        if el and not el.input_value():
                            el.fill(val)
                    except Exception:
                        pass

                # Check terms / consent checkboxes
                for cb in page.query_selector_all("input[type='checkbox']"):
                    try:
                        if not cb.is_checked():
                            cb.check()
                    except Exception:
                        pass

                # 4. Attempt Form Submission
                submit_btn = page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Submit Application'), button:has-text('Submit'), button:has-text('Complete Application')")
                if not submit_btn:
                    browser.close()
                    return False, f"Could not find a direct submittable application form on {company} portal.", None, None

                submit_btn.click()
                time.sleep(4.0)

                # 5. Strict Confirmation Verification
                is_confirmed, conf_msg, screenshot_path, ref_id = verifier.verify_page_submission(
                    page=page,
                    job=job,
                    candidate_info=personal_info
                )

                browser.close()

                if is_confirmed:
                    print(f"[BrowserApplier] ✅ Direct Portal Submission Confirmed: {conf_msg}")
                    return True, conf_msg, screenshot_path, ref_id
                else:
                    print(f"[BrowserApplier] ❌ Confirmation failed: {conf_msg}")
                    return False, f"Direct submission unconfirmed: {conf_msg}", None, None

        except Exception as e:
            print(f"[BrowserApplier Error] {e}")
            return False, f"Direct portal automation error: {str(e)[:80]}", None, None

browser_applier = PlaywrightBrowserApplier()
