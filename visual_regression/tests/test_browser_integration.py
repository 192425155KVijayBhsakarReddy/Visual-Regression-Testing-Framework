import pytest
import os
import time
from visual_regression.capture.browser_manager import BrowserManager
from visual_regression.capture.screenshot_capture import ScreenshotCapture
from visual_regression.vision.image_processor import ImageProcessor

def test_headless_chrome_capture(tmp_path):
    """Integration Test: Launches headless Chrome, navigates to data URL, and captures screenshot."""
    output_png = str(tmp_path / "integration_test.png")
    # Data URL containing simple HTML to test standalone without needing external web servers
    test_html_url = "data:text/html,<html><body style='background:%232563eb;'><h1 style='color:white;'>Integration Test</h1></body></html>"

    result = ScreenshotCapture.capture(
        url=test_html_url,
        output_path=output_png,
        viewport_key="desktop",
        wait_seconds=0.5,
        headless=True
    )

    assert result["success"] is True
    assert os.path.exists(output_png)

    # Validate image can be loaded with OpenCV
    img = ImageProcessor.load_image(output_png)
    assert img.shape[0] == 768
    assert img.shape[1] == 1366

