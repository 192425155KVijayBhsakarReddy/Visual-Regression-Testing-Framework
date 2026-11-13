import os
import shutil
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from visual_regression.config import Config

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

logger = logging.getLogger("BrowserManager")

class BrowserManager:
    """Manages headless and standard Chromium/ChromeDriver lifecycles with robust fallback options."""

    @staticmethod
    def get_chrome_options(headless: bool = True, width: int = 1366, height: int = 768) -> Options:
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument(f"--window-size={width},{height}")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--force-device-scale-factor=1")
        options.add_argument("--log-level=3")

        # Specific custom binary path if running on Windows or Docker
        custom_chrome_bin = os.environ.get("CHROME_BIN")
        if custom_chrome_bin and os.path.exists(custom_chrome_bin):
            options.binary_location = custom_chrome_bin
        elif os.path.exists("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"):
            options.binary_location = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        elif shutil.which("chromium"):
            options.binary_location = shutil.which("chromium")
        elif shutil.which("google-chrome"):
            options.binary_location = shutil.which("google-chrome")

        return options

    @classmethod
    def create_driver(cls, width: int = 1366, height: int = 768, headless: bool = True) -> webdriver.Chrome:
        """Instantiates and returns a configured Chrome WebDriver."""
        options = cls.get_chrome_options(headless=headless, width=width, height=height)
        
        # In Selenium 4.6+, Selenium Manager automatically handles driver resolution if not explicitly set.
        # We try standard Service() first, falling back to ChromeDriverManager if needed.
        driver = None
        errors = []

        try:
            driver = webdriver.Chrome(options=options)
        except Exception as e1:
            errors.append(f"Standard Selenium Manager initialization failed: {str(e1)}")
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                except Exception as e2:
                    errors.append(f"ChromeDriverManager fallback failed: {str(e2)}")
            if not driver:
                raise RuntimeError("Failed to launch Chrome browser: " + " | ".join(errors))

        # Explicitly set window dimensions
        driver.set_window_size(width, height)
        # Set viewport metrics via CDP (Chrome DevTools Protocol) so screenshot perfectly matches requested resolution
        try:
            driver.execute_cdp_cmd(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": width,
                    "height": height,
                    "deviceScaleFactor": 1,
                    "mobile": False
                }
            )
        except Exception:
            pass
        driver.set_page_load_timeout(Config.SELENIUM_TIMEOUT)
        return driver
