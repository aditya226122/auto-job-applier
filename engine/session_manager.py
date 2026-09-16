import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import config

SESSIONS_DIR = Path(config.BASE_DIR) / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

class SessionManager:
    """Manages persistent browser storage states and authentication cookies for job portals."""
    
    PORTALS = {
        "linkedin": {
            "name": "LinkedIn",
            "domain": ".linkedin.com",
            "login_url": "https://www.linkedin.com/login",
            "check_url": "https://www.linkedin.com/feed/",
            "auth_indicator": "global-nav"
        },
        "naukri": {
            "name": "Naukri.com",
            "domain": ".naukri.com",
            "login_url": "https://www.naukri.com/nlogin/login",
            "check_url": "https://www.naukri.com/mnjuser/homepage",
            "auth_indicator": "nI-gNb-drawer"
        },
        "unstop": {
            "name": "Unstop (Dare2Compete)",
            "domain": ".unstop.com",
            "login_url": "https://unstop.com/auth/login",
            "check_url": "https://unstop.com/dashboard",
            "auth_indicator": "user_profile"
        },
        "indeed": {
            "name": "Indeed India",
            "domain": ".indeed.com",
            "login_url": "https://secure.indeed.com/account/login",
            "check_url": "https://in.indeed.com/",
            "auth_indicator": "gnav-AccountMenu"
        }
    }

    def __init__(self):
        self.sessions_dir = SESSIONS_DIR

    def _normalize_portal_key(self, portal_name: str) -> str:
        name = portal_name.lower()
        if "linkedin" in name:
            return "linkedin"
        elif "naukri" in name:
            return "naukri"
        elif "unstop" in name or "dare2compete" in name:
            return "unstop"
        elif "indeed" in name:
            return "indeed"
        return name.replace(" ", "_")

    def get_session_file_path(self, portal: str) -> Path:
        key = self._normalize_portal_key(portal)
        return self.sessions_dir / f"{key}_state.json"

    def has_valid_session(self, portal: str) -> bool:
        """Checks if a storage state file exists and has non-expired cookies."""
        file_path = self.get_session_file_path(portal)
        if not file_path.exists():
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cookies = data.get("cookies", [])
                if not cookies:
                    return False
                now_ts = datetime.datetime.now().timestamp()
                valid_cookies = [c for c in cookies if c.get("expires", now_ts + 100) > now_ts]
                return len(valid_cookies) > 0
        except Exception:
            return False

    def get_all_session_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Returns the current login / session status for all supported platforms."""
        statuses = {}
        for key, info in self.PORTALS.items():
            file_path = self.get_session_file_path(key)
            has_session = self.has_valid_session(key)
            last_updated = None
            cookie_count = 0
            
            if file_path.exists():
                try:
                    mtime = os.path.getmtime(file_path)
                    last_updated = datetime.datetime.fromtimestamp(mtime).strftime("%d %b %Y, %I:%M %p")
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        cookie_count = len(data.get("cookies", []))
                except Exception:
                    pass

            statuses[key] = {
                "name": info["name"],
                "is_authenticated": has_session,
                "login_url": info["login_url"],
                "last_updated": last_updated,
                "cookie_count": cookie_count,
                "session_file": str(file_path)
            }
        return statuses

session_manager = SessionManager()
