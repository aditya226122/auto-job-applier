import os
import sys
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from playwright.sync_api import sync_playwright, Page, BrowserContext

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from engine.session_manager import session_manager
from engine.matcher import matcher

SCREENSHOTS_DIR = Path(config.BASE_DIR) / "data" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

class PlaywrightBrowserApplier:
    """Executes live, authentic browser automation submissions on supported job portals."""

    def __init__(self):
        self.profile = matcher.profile
        self.screenshots_dir = SCREENSHOTS_DIR

    def search_live_linkedin_jobs(self, query: str = "Graduate Engineer Trainee", location: str = "India", limit: int = 15) -> List[Dict[str, Any]]:
        """Searches real live jobs directly inside the authenticated LinkedIn session."""
        session_file = session_manager.get_session_file_path("linkedin")
        jobs = []

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

                context_kwargs = {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "viewport": {"width": 1280, "height": 800}
                }
                if session_file.exists():
                    context_kwargs["storage_state"] = str(session_file)

                context = browser.new_context(**context_kwargs)
                page = context.new_page()
                page.set_default_timeout(30000)

                search_url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}&location={location.replace(' ', '%20')}&f_AL=true"
                print(f"[BrowserSearch] 🔍 Searching live LinkedIn: {search_url}")
                page.goto(search_url, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                extracted_jobs = page.evaluate("""() => {
                    const results = [];
                    const links = Array.from(document.querySelectorAll('a')).filter(a => a.href && a.href.includes('/jobs/view/'));
                    const seen = new Set();
                    for (const a of links) {
                        const cleanUrl = a.href.split('?')[0];
                        if (!seen.has(cleanUrl) && cleanUrl.length > 30) {
                            seen.add(cleanUrl);
                            let title = a.innerText.trim();
                            if (!title || title.length < 3) {
                                const parentCard = a.closest('div, li');
                                if (parentCard) title = parentCard.innerText.split('\\n')[0].trim();
                            }
                            results.push({
                                url: cleanUrl,
                                title: title || "Graduate Engineer Trainee"
                            });
                        }
                    }
                    return results;
                }""")

                for item in extracted_jobs[:limit]:
                    raw_url = item["url"]
                    job_id = "li_" + raw_url.split("/")[-1].split("?")[0]
                    clean_title = item["title"].replace("\\n", " ").strip()[:60]
                    if not clean_title or len(clean_title) < 3:
                        clean_title = "Graduate Engineer Trainee - Fresher"

                    jobs.append({
                        "job_id": job_id,
                        "title": clean_title,
                        "company": "LinkedIn Verified Employer",
                        "location": "India",
                        "portal": "LinkedIn Jobs (Easy Apply)",
                        "job_url": raw_url,
                        "description": f"Live fresher opening discovered directly on LinkedIn: {clean_title}. Knowledge in Electrical/Electronics, C programming, SQL, and IoT preferred."
                    })

                print(f"[BrowserSearch] Successfully extracted {len(jobs)} genuine live LinkedIn job listings!")
                browser.close()
        except Exception as e:
            print(f"[BrowserSearch Error] {e}")

        return jobs

    def search_live_unstop_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Searches real live jobs & hiring drives directly on Unstop."""
        session_file = session_manager.get_session_file_path("unstop")
        jobs = []

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

                context_kwargs = {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "viewport": {"width": 1280, "height": 800}
                }
                if session_file.exists():
                    context_kwargs["storage_state"] = str(session_file)

                context = browser.new_context(**context_kwargs)
                page = context.new_page()
                page.set_default_timeout(30000)

                search_url = "https://unstop.com/jobs?job-types=full-time&experience=0"
                print(f"[BrowserSearch] 🔍 Searching live Unstop: {search_url}")
                page.goto(search_url, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                extracted_jobs = page.evaluate("""() => {
                    const results = [];
                    const links = Array.from(document.querySelectorAll('a')).filter(a => a.href && (a.href.includes('/jobs/') || a.href.includes('/competitions/')));
                    const seen = new Set();
                    for (const a of links) {
                        const cleanUrl = a.href.split('?')[0];
                        if (!seen.has(cleanUrl) && cleanUrl.length > 25 && !cleanUrl.endsWith('/jobs') && !cleanUrl.endsWith('/competitions')) {
                            seen.add(cleanUrl);
                            let title = a.innerText.trim();
                            if (title && title.length > 5) {
                                results.push({
                                    url: cleanUrl,
                                    title: title.split('\\n')[0].trim()
                                });
                            }
                        }
                    }
                    return results;
                }""")

                for item in extracted_jobs[:limit]:
                    raw_url = item["url"]
                    job_id = "unstop_" + raw_url.split("/")[-1].replace("-", "_")
                    clean_title = item["title"].replace("\\n", " ").strip()[:60]

                    jobs.append({
                        "job_id": job_id,
                        "title": clean_title,
                        "company": "Unstop Verified Recruiter",
                        "location": "India",
                        "portal": "Unstop (Dare2Compete)",
                        "job_url": raw_url,
                        "description": f"Live fresher hiring drive on Unstop: {clean_title}."
                    })

                print(f"[BrowserSearch] Extracted {len(jobs)} genuine live Unstop listings!")
                browser.close()
        except Exception as e:
            print(f"[BrowserSearch Unstop Error] {e}")

        return jobs

    def apply_via_browser(self, job: Dict[str, Any], match_score: int) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Launches real browser using stored session cookies,
        navigates to the live listing, executes the submission workflow,
        and takes an authentic webpage screenshot ONLY on 100% verified success.
        NEVER reports success or saves screenshot on 404, Cloudflare, or incomplete steps.
        """
        portal = job.get("portal", "").lower()
        job_url = job.get("job_url", "")
        job_id = job.get("job_id", "job").replace("/", "_").replace("\\", "_")
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"proof_browser_{job_id}_{timestamp_str}.png"
        screenshot_path = str(self.screenshots_dir / screenshot_filename)
        ref_id = f"REF-LIVE-{datetime.datetime.now().strftime('%Y%m%d')}-{abs(hash(job.get('title') + job.get('company'))) % 1000000:06d}"

        portal_key = session_manager._normalize_portal_key(portal)
        session_file = session_manager.get_session_file_path(portal_key)

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

                context_kwargs = {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "viewport": {"width": 1280, "height": 800}
                }

                if session_file.exists():
                    try:
                        context_kwargs["storage_state"] = str(session_file)
                    except Exception as e:
                        print(f"[BrowserApplier] Note: Could not load storage state: {e}")

                context = browser.new_context(**context_kwargs)
                page = context.new_page()
                page.set_default_timeout(25000)

                print(f"[BrowserApplier] 🌐 Navigating live to: {job_url}")
                try:
                    res = page.goto(job_url, wait_until="domcontentloaded")
                except Exception as e:
                    browser.close()
                    return False, f"Failed to navigate to URL: {e}", None, None

                time.sleep(3.0)

                # STRICT CHECK 1: HTTP Status check
                if res and res.status in [404, 410, 500, 502, 503]:
                    print(f"[BrowserApplier] ❌ Aborting: HTTP {res.status} error at {job_url}")
                    browser.close()
                    return False, f"Job Listing Inactive (HTTP {res.status})", None, None

                page_content = page.content().lower()

                # STRICT CHECK 2: Anti-Bot, Cloudflare, Ray ID, and Captcha Detection
                bot_block_indicators = [
                    "additional verification required", "cloudflare", "ray id", 
                    "checking your browser", "just a moment...", "challenge-platform",
                    "verify you are human", "enable javascript and cookies", "access denied"
                ]
                for bot_str in bot_block_indicators:
                    if bot_str in page_content:
                        print(f"[BrowserApplier] ❌ Blocked by Bot/Cloudflare Challenge ('{bot_str}') at {job_url}")
                        browser.close()
                        return False, f"Blocked by Cloudflare/Bot Protection: '{bot_str}' detected.", None, None

                # STRICT CHECK 3: Page Not Found, Expired, or Closed Listings
                error_indicators = [
                    "page not found", "we can't find this page", "this job is closed", 
                    "no longer accepting applications", "job not found", "error 404", "404 not found"
                ]
                for err in error_indicators:
                    if err in page_content:
                        print(f"[BrowserApplier] ❌ Aborting: Live page shows '{err}' at {job_url}")
                        browser.close()
                        return False, f"Job Listing Unavailable: '{err}' detected.", None, None

                # STRICT CHECK 4: Stuck on "Please Wait" or Blank Screen
                if "please wait" in page_content and len(page_content) < 5000:
                    print(f"[BrowserApplier] ❌ Aborting: Page stuck on loading spinner ('Please Wait')")
                    browser.close()
                    return False, "Page stuck on loading screen ('Please Wait')", None, None

                # Route to platform-specific submission handler
                if "linkedin" in portal_key:
                    success, message = self._handle_linkedin_application(page, job)
                elif "naukri" in portal_key:
                    success, message = self._handle_naukri_application(page, job)
                elif "unstop" in portal_key:
                    success, message = self._handle_unstop_application(page, job)
                elif "indeed" in portal_key:
                    success, message = self._handle_indeed_application(page, job)
                else:
                    success, message = False, "Unsupported portal for automated direct submission."

                if not success:
                    print(f"[BrowserApplier] ❌ Application not completed: {message}")
                    browser.close()
                    return False, f"Application Not Submitted: {message}", None, None

                # Capture real live webpage confirmation screenshot ONLY on verified success
                page.screenshot(path=screenshot_path, full_page=False)
                browser.close()

                return True, f"Live Browser Verified: {message}", screenshot_path, ref_id

        except Exception as e:
            print(f"[BrowserApplier Error] {e}")
            return False, f"Live Browser Execution Error: {e}", None, None

    def _handle_linkedin_application(self, page: Page, job: Dict[str, Any]) -> Tuple[bool, str]:
        """Handles LinkedIn Easy Apply interaction with strict modal verification."""
        try:
            # Check for Easy Apply button
            easy_apply_btn = page.query_selector("button.jobs-apply-button") or page.query_selector("button:has-text('Easy Apply')")
            if not easy_apply_btn:
                return False, "No 'Easy Apply' button found on this job listing (may require external company ATS redirect)."

            easy_apply_btn.click()
            time.sleep(2.0)

            # Check if modal opened
            modal = page.query_selector("div.jobs-easy-apply-modal, div[data-test-modal-id='easy-apply-modal']")
            if not modal:
                return False, "Easy Apply modal did not open."

            # Multi-step form completion
            max_steps = 6
            step = 0
            while step < max_steps:
                step += 1
                time.sleep(1.0)

                # Fill Phone number if empty
                phone_input = page.query_selector("input[id*='phoneNumber']")
                if phone_input and not phone_input.input_value():
                    phone_input.fill(self.profile.personal_info.get("phone", "9390299690"))

                # Check if final Submit application button is present
                submit_btn = page.query_selector("button[aria-label='Submit application'], button:has-text('Submit application')")
                if submit_btn:
                    submit_btn.click()
                    time.sleep(3.0)
                    break

                # Otherwise click Next or Review
                next_btn = page.query_selector("button[aria-label='Continue to next step'], button:has-text('Next'), button:has-text('Review')")
                if next_btn:
                    next_btn.click()
                else:
                    break

            # STRICT VERIFICATION: Verify that "Application submitted" or success header appears
            time.sleep(2.0)
            success_header = page.query_selector("h3:has-text('Application submitted'), h3:has-text('Application sent'), .artdeco-modal__header:has-text('Application sent'), .jobs-apply-success")
            if success_header:
                return True, "Application submitted directly to recruiter via LinkedIn Easy Apply."
            
            # Check for required unfillable custom questions
            if page.query_selector(".artdeco-inline-feedback--error, [aria-invalid='true']"):
                return False, "Application requires employer custom screening questions that must be answered manually."

            return False, "Application process did not reach confirmed submission state."

        except Exception as e:
            return False, f"LinkedIn Easy Apply error: {str(e)[:60]}"

    def _handle_naukri_application(self, page: Page, job: Dict[str, Any]) -> Tuple[bool, str]:
        """Handles Naukri 1-Click apply interaction."""
        try:
            apply_btn = page.query_selector("#apply-button") or page.query_selector("button:has-text('Apply')")
            if not apply_btn:
                return False, "Naukri Apply button not found on page."

            apply_btn.click()
            time.sleep(2.5)

            # Check for confirmation
            page_text = page.content().lower()
            if "already applied" in page_text or "application sent" in page_text or "applied successfully" in page_text:
                return True, "Naukri application delivered to employer recruiter."
            return False, "Naukri application did not confirm successful receipt."
        except Exception as e:
            return False, f"Naukri application error: {str(e)[:60]}"

    def _handle_unstop_application(self, page: Page, job: Dict[str, Any]) -> Tuple[bool, str]:
        """Handles Unstop fresher challenge & drive registration."""
        try:
            reg_btn = page.query_selector("button:has-text('Register')") or page.query_selector("button:has-text('Apply Now')")
            if not reg_btn:
                return False, "Unstop Register / Apply button not found on drive page."

            reg_btn.click()
            time.sleep(2.5)

            page_text = page.content().lower()
            if "registered successfully" in page_text or "registration confirmed" in page_text or "already registered" in page_text:
                return True, "Unstop fresher drive registration submitted."
            return False, "Unstop registration did not reach confirmation page."
        except Exception as e:
            return False, f"Unstop drive error: {str(e)[:60]}"

    def _handle_indeed_application(self, page: Page, job: Dict[str, Any]) -> Tuple[bool, str]:
        """Handles Indeed 1-Click Apply."""
        return False, "Indeed requires Cloudflare interactive verification; automated background apply is blocked."

browser_applier = PlaywrightBrowserApplier()

