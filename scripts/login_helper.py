import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from playwright.sync_api import sync_playwright
from engine.session_manager import session_manager

def interactive_login(portal_key: str = "linkedin"):
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
    print("3. Once you see your homepage/feed, return here and press ENTER.")
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

        input("👉 Press ENTER here after you have successfully logged in in the browser... ")

        # Save authenticated storage state
        context.storage_state(path=str(session_file))
        print(f"✅ Session cookies & authentication state saved to: {session_file}")
        browser.close()

    if session_manager.has_valid_session(portal_key):
        print(f"🎉 Verified: Valid session active for {portal_info['name']}!")
        return True
    else:
        print(f"⚠️ Warning: Could not verify valid session for {portal_info['name']}.")
        return False

if __name__ == "__main__":
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
