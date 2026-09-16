import os
import sys
import time
import argparse
from pathlib import Path

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from playwright.sync_api import sync_playwright
from engine.session_manager import session_manager

def interactive_login(portal_key: str = "linkedin", max_wait_seconds: int = 300):
    portal_info = session_manager.PORTALS.get(portal_key)
    if not portal_info:
        print(f"[Error] Unknown portal: {portal_key}")
        return False

    session_file = session_manager.get_session_file_path(portal_key)
    print("\n=======================================================")
    print(f"🔐 Interactive Login Helper for: {portal_info['name']}")
    print("A visible browser window will open now.")
    print("1. Log in with your candidate email/password.")
    print("2. Complete any 2FA/OTP or CAPTCHA if prompted.")
    print("3. When you reach your dashboard, click the green '💾 Save Session' button on the page OR press ENTER in the terminal!")
    print("=======================================================\n")

    with sync_playwright() as p:
        browser = None
        for ch in ["msedge", "chrome", None]:
            try:
                launch_kwargs = {"headless": False}
                if ch:
                    launch_kwargs["channel"] = ch
                browser = p.chromium.launch(**launch_kwargs)
                break
            except Exception:
                continue

        if not browser:
            browser = p.chromium.launch(headless=False)

        context_args = {}
        if session_file.exists():
            try:
                context_args["storage_state"] = str(session_file)
            except Exception:
                pass

        context = browser.new_context(**context_args)
        page = context.new_page()

        print(f"🌐 Navigating to {portal_info['login_url']}...")
        page.goto(portal_info["login_url"])

        # Inject helper script on navigation
        def inject_helper():
            try:
                page.evaluate("""() => {
                    if (document.getElementById('save-session-helper-btn')) return;
                    const btn = document.createElement('button');
                    btn.id = 'save-session-helper-btn';
                    btn.innerHTML = '💾 Click to Save Session & Finish';
                    btn.style.position = 'fixed';
                    btn.style.top = '12px';
                    btn.style.right = '20px';
                    btn.style.zIndex = '2147483647';
                    btn.style.backgroundColor = '#16a34a';
                    btn.style.color = '#ffffff';
                    btn.style.border = '2px solid #ffffff';
                    btn.style.padding = '10px 18px';
                    btn.style.borderRadius = '30px';
                    btn.style.fontSize = '14px';
                    btn.style.fontWeight = 'bold';
                    btn.style.cursor = 'pointer';
                    btn.style.boxShadow = '0 6px 16px rgba(0,0,0,0.35)';
                    btn.onclick = () => {
                        window.__save_session_clicked = true;
                        btn.innerHTML = '✅ Saving session...';
                        btn.style.backgroundColor = '#2563eb';
                    };
                    document.body.appendChild(btn);
                }""")
            except Exception:
                pass

        print("⏳ Waiting for you to sign in in the popup browser (Auto-detecting login)...")
        start_time = time.time()
        logged_in = False

        while time.time() - start_time < max_wait_seconds:
            time.sleep(2)
            try:
                if page.is_closed():
                    print("Browser window was closed by user. Saving session state...")
                    break

                inject_helper()
                
                # Check 1: User clicked the floating green button
                try:
                    is_clicked = page.evaluate("() => window.__save_session_clicked === true")
                    if is_clicked:
                        print("🎉 'Save Session' button clicked by user in browser!")
                        time.sleep(1.5)
                        logged_in = True
                        break
                except Exception:
                    pass

                # Check 2: DOM selectors indicating authenticated profile
                auth_selectors = [
                    ".nI-gNb-drawer", ".user-profile", "#ni-gnb-header", "a[href*='logout']",
                    ".view-profile-wrapper", "app-user-profile", ".user_profile", "a[href*='dashboard']",
                    "button:has-text('Logout')", ".global-nav__me", ".profile-icon", ".avatar"
                ]
                for sel in auth_selectors:
                    if page.query_selector(sel):
                        print(f"🎉 Login detected via element: {sel}!")
                        time.sleep(2)
                        logged_in = True
                        break
                if logged_in:
                    break

                # Check 3: URL change
                current_url = page.url.lower()
                if any(ind in current_url for ind in ["homepage", "dashboard", "feed", "profile", "my-activity", "candidate-dashboard"]):
                    print(f"🎉 Login detected via URL: {page.url}!")
                    time.sleep(2)
                    logged_in = True
                    break

                # Check 4: Check if substantial auth cookies are set
                cookies = context.cookies()
                auth_cookie_names = ["surf", "nk_id", "is_logged_in", "unstop_session", "remember_web", "li_at", "ctk", "user_id"]
                has_auth_cookie = any(any(ac in c.get("name", "").lower() for ac in auth_cookie_names) for c in cookies)
                if has_auth_cookie and ("login" not in current_url or "homepage" in current_url):
                    print(f"🎉 Auth session cookies detected ({len(cookies)} cookies found)!")
                    time.sleep(2)
                    logged_in = True
                    break

            except Exception:
                pass

        # Save authenticated storage state
        try:
            context.storage_state(path=str(session_file))
            print(f"✅ Session cookies & authentication state saved to: {session_file}")
            browser.close()
        except Exception as e:
            print(f"Note saving state: {e}")

    if session_manager.has_valid_session(portal_key):
        print(f"🎉 Verified: Valid session active for {portal_info['name']}!")
        return True
    else:
        print(f"⚠️ Note: Session saved to {session_file}. Verify in Dashboard Tab 5.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Portal Session Login Helper")
    parser.add_argument("portal", nargs="?", default=None, help="Portal to log in (linkedin, naukri, unstop, indeed)")
    args = parser.parse_args()

    if args.portal:
        interactive_login(session_manager._normalize_portal_key(args.portal))
    else:
        print("Choose platform to log in:")
        print("1. LinkedIn")
        print("2. Naukri.com")
        print("3. Unstop (Dare2Compete)")
        print("4. Indeed India")
        print("5. Check current session status")
        
        choice = input("Enter choice (1-5): ").strip()
        mapping = {"1": "linkedin", "2": "naukri", "3": "unstop", "4": "indeed"}
        if choice in mapping:
            interactive_login(mapping[choice])
        elif choice == "5":
            statuses = session_manager.get_all_session_statuses()
            for k, v in statuses.items():
                status_emoji = "✅ Active" if v["is_authenticated"] else "❌ Not Authenticated"
                print(f"{v['name']}: {status_emoji} (Cookies: {v['cookie_count']}, Last: {v['last_updated']})")
        else:
            print("Invalid choice.")

