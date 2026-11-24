import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Auto-load local .env file if available
env_path = BASE_DIR.parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "visual-regression-secret-key-prod-2026")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "visual_regression.db"))
    
    # Storage directories
    STORAGE_DIR = BASE_DIR / "storage"
    BASELINES_DIR = STORAGE_DIR / "baselines"
    SCREENSHOTS_DIR = STORAGE_DIR / "screenshots"
    DIFFS_DIR = STORAGE_DIR / "diffs"
    HEATMAPS_DIR = STORAGE_DIR / "heatmaps"
    REPORTS_DIR = STORAGE_DIR / "reports"
    
    # Visual comparison defaults
    DEFAULT_THRESHOLD = float(os.environ.get("DEFAULT_THRESHOLD", "0.5"))  # 0.5%
    DEFAULT_VIEWPORT = os.environ.get("DEFAULT_VIEWPORT", "1366x768")
    
    # Supported Viewports (width x height)
    SUPPORTED_VIEWPORTS = {
        "desktop": {"width": 1366, "height": 768, "label": "Desktop (1366x768)"},
        "laptop": {"width": 1280, "height": 800, "label": "Laptop (1280x800)"},
        "tablet": {"width": 768, "height": 1024, "label": "Tablet (768x1024)"},
        "mobile": {"width": 375, "height": 812, "label": "Mobile (375x812)"}
    }
    
    # Browser config
    HEADLESS = os.environ.get("SELENIUM_HEADLESS", "true").lower() in ("true", "1", "yes")
    SELENIUM_TIMEOUT = int(os.environ.get("SELENIUM_TIMEOUT", "15"))

    # Jira Cloud Integration config
    JIRA_URL = os.environ.get("JIRA_URL", "https://07vijay.atlassian.net")
    JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "192425155.simats@saveetha.com")
    JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
    JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "VRF")
    JIRA_AUTO_CREATE_ON_FAIL = os.environ.get("JIRA_AUTO_CREATE_ON_FAIL", "true").lower() in ("true", "1", "yes")

    @classmethod
    def init_directories(cls):
        for directory in [
            cls.STORAGE_DIR,
            cls.BASELINES_DIR,
            cls.SCREENSHOTS_DIR,
            cls.DIFFS_DIR,
            cls.HEATMAPS_DIR,
            cls.REPORTS_DIR
        ]:
            directory.mkdir(parents=True, exist_ok=True)

