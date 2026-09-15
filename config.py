import os
from pathlib import Path

# Safe .env loader without requiring external packages
BASE_DIR = Path(__file__).resolve().parent
env_file = BASE_DIR / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Candidate Configuration
CANDIDATE_PROFILE_PATH = BASE_DIR / "data" / "candidate_profile.json"
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "udayalakshmiboddu83@gmail.com")

# Email / SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_NAME = os.getenv("SENDER_NAME", "AI Job Agent")
EMAIL_NOTIFICATIONS_ENABLED = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "True").lower() in ("true", "1", "yes")

# Job Search & Application Limits (Full 24-Hour Schedule: 12:00 AM to 11:59 PM)
MAX_DAILY_APPLICATIONS = int(os.getenv("MAX_DAILY_APPLICATIONS", "24"))
MIN_DAILY_APPLICATIONS = int(os.getenv("MIN_DAILY_APPLICATIONS", "20"))
HOURLY_APPLICATIONS_MIN = int(os.getenv("HOURLY_APPLICATIONS_MIN", "1"))
HOURLY_APPLICATIONS_MAX = int(os.getenv("HOURLY_APPLICATIONS_MAX", "3"))
ACTIVE_HOURS_START = int(os.getenv("ACTIVE_HOURS_START", "0"))   # 12:00 AM Midnight
ACTIVE_HOURS_END = int(os.getenv("ACTIVE_HOURS_END", "23"))      # 11:59 PM End of Day
MIN_MATCH_SCORE = int(os.getenv("MIN_MATCH_SCORE", "60"))

# Database
DB_PATH = BASE_DIR / "data" / "job_applications.db"

# Gemini / LLM API Key (optional for enhanced dynamic answering & matching)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Automation settings
HEADLESS_BROWSER = os.getenv("HEADLESS_BROWSER", "False").lower() in ("true", "1", "yes")
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "False").lower() in ("true", "1", "yes")
