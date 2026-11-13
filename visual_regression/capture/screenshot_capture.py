import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from visual_regression.config import Config
from visual_regression.capture.browser_manager import BrowserManager
from visual_regression.vision.layout_analyzer import LayoutAnalyzer

logger = logging.getLogger("ScreenshotCapture")

class ScreenshotCapture:
    """Orchestrates headless web page navigation, wait stability, and high-fidelity screenshot capturing."""

    @classmethod
    def capture(
        cls,
        url: str,
        output_path: str,
        viewport_key: str = "desktop",
        wait_seconds: float = 1.0,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Navigates to URL, waits for rendering stability, captures full viewport screenshot,
        and extracts DOM structural hierarchy.
        """
        vp = Config.SUPPORTED_VIEWPORTS.get(viewport_key, {"width": 1366, "height": 768})
        width = vp["width"]
        height = vp["height"]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        driver = None
        start_time = time.time()

        try:
            logger.info("Launching browser to capture %s at %sx%s", url, width, height)
            driver = BrowserManager.create_driver(width=width, height=height, headless=headless)
            driver.get(url)

            # Wait for DOM and initial CSS render
            time.sleep(wait_seconds)

            # Extract DOM elements snapshot before taking screenshot
            dom_elements = LayoutAnalyzer.extract_dom_snapshot(driver)

            # Capture screenshot
            success = driver.save_screenshot(output_path)
            if not success or not os.path.exists(output_path):
                raise RuntimeError(f"Selenium failed to write screenshot to {output_path}")

            browser_name = driver.capabilities.get("browserName", "chrome")
            browser_version = driver.capabilities.get("browserVersion", "unknown")

            return {
                "success": True,
                "screenshot_path": output_path,
                "width": width,
                "height": height,
                "viewport": f"{width}x{height}",
                "dom_elements": dom_elements,
                "browser_info": f"{browser_name} {browser_version}",
                "elapsed_time": round(time.time() - start_time, 2)
            }

        except Exception as e:
            logger.error("Screenshot capture failed for %s: %s", url, str(e))
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "viewport": f"{width}x{height}"
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

