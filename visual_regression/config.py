import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

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

