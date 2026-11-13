import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from visual_regression.config import Config
from visual_regression.database import get_db_connection
from visual_regression.capture.screenshot_capture import ScreenshotCapture
from visual_regression.vision.image_processor import ImageProcessor
from visual_regression.vision.visual_comparator import VisualComparator
from visual_regression.vision.heatmap_generator import HeatmapGenerator
from visual_regression.vision.layout_analyzer import LayoutAnalyzer

logger = logging.getLogger("TestService")

class TestService:
    """End-to-end execution of visual regression tests, defect classification, and result recording."""

    @classmethod
    def run_test(
        cls,
        application_id: int,
        test_url: str,
        viewport_key: str = "desktop",
        baseline_id: Optional[int] = None,
        custom_threshold: Optional[float] = None,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Executes a complete test run:
        1. Validates or fetches baseline
        2. Captures current viewport screenshot & DOM snapshot
        3. Executes OpenCV image diff & contour detection
        4. Generates heatmap overlay
        5. Performs DOM layout diff
        6. Persists test execution & defects in SQLite
        """
        conn = get_db_connection()
        app = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
        if not app:
            conn.close()
            return {"success": False, "error": f"Application #{application_id} not found"}

        vp = Config.SUPPORTED_VIEWPORTS.get(viewport_key, {"width": 1366, "height": 768})
        viewport_str = f"{vp['width']}x{vp['height']}"
        threshold = custom_threshold if custom_threshold is not None else float(app["default_threshold"] or Config.DEFAULT_THRESHOLD)

        # 1. Fetch baseline
        baseline = None
        if baseline_id:
            baseline = conn.execute("SELECT * FROM baselines WHERE id = ?", (baseline_id,)).fetchone()
        else:
            baseline = conn.execute(
                "SELECT * FROM baselines WHERE application_id = ? AND page_url = ? AND viewport = ?",
                (application_id, test_url, viewport_str)
            ).fetchone()

        if not baseline:
            conn.close()
            return {
                "success": False,
                "error": f"No baseline found for {test_url} with viewport {viewport_str}. Please create or upload a baseline first."
            }

        baseline_file = baseline["file_path"]
        if not os.path.exists(baseline_file):
            conn.close()
            return {"success": False, "error": f"Baseline file missing on disk: {baseline_file}"}

        # 2. Capture current screenshot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"run_app{application_id}_{viewport_str}_{timestamp}.png"
        screenshot_path = str(Config.SCREENSHOTS_DIR / screenshot_filename)

        cap_result = ScreenshotCapture.capture(
            url=test_url,
            output_path=screenshot_path,
            viewport_key=viewport_key,
            headless=headless
        )

        if not cap_result["success"]:
            # Record failed execution due to error
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO test_executions 
                   (application_id, baseline_id, test_url, viewport, threshold, screenshot_path, status, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, 'ERROR', ?)""",
                (application_id, baseline["id"], test_url, viewport_str, threshold, "", cap_result.get("error", "Browser failed"))
            )
            exec_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return {"success": False, "test_id": exec_id, "error": cap_result.get("error")}

        # 3. Load baseline and current images
        try:
            base_img = ImageProcessor.load_image(baseline_file)
            curr_img = ImageProcessor.load_image(screenshot_path)
        except Exception as e:
            conn.close()
            return {"success": False, "error": f"Image load failed: {str(e)}"}

        # 4. Computer Vision comparison
        comparator = VisualComparator()
        comp_result = comparator.compare(
            baseline_img=base_img,
            current_img=curr_img,
            acceptable_threshold_percent=threshold
        )

        # 5. Save visual difference overlay
        diff_filename = f"diff_app{application_id}_{timestamp}.png"
        diff_path = str(Config.DIFFS_DIR / diff_filename)
        ImageProcessor.save_image(comp_result["diff_overlay"], diff_path)

        # 6. Generate and save difference heatmap
        heatmap_filename = f"heatmap_app{application_id}_{timestamp}.png"
        heatmap_path = str(Config.HEATMAPS_DIR / heatmap_filename)
        heatmap_img = HeatmapGenerator.generate_heatmap(
            gray_diff=comp_result["gray_diff"],
            current_img=curr_img
        )
        ImageProcessor.save_image(heatmap_img, heatmap_path)

        # 7. DOM Layout Analysis
        base_dom = []
        if baseline["dom_snapshot"]:
            try:
                base_dom = json.loads(baseline["dom_snapshot"])
            except Exception:
                base_dom = []
        curr_dom = cap_result.get("dom_elements", [])
        dom_defects = LayoutAnalyzer.compare_layouts(base_dom, curr_dom)

        # Combine defects
        all_defects = []
        # Add visual defect boxes
        for box in comp_result["bounding_boxes"]:
            all_defects.append({
                "defect_type": "visual_difference",
                "description": f"Visual pixel variance detected ({box['width']}x{box['height']} px)",
                "x": box["x"],
                "y": box["y"],
                "width": box["width"],
                "height": box["height"],
                "severity": "HIGH" if comp_result["status"] == "FAIL" else "LOW"
            })
        # Add DOM layout defects
        all_defects.extend(dom_defects)

        # 8. Persist in database
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO test_executions 
               (application_id, baseline_id, test_url, viewport, threshold, screenshot_path, diff_path, heatmap_path,
                total_pixels, changed_pixels, difference_percentage, ssim_score, status, browser_info, dom_changes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                application_id,
                baseline["id"],
                test_url,
                viewport_str,
                threshold,
                screenshot_path,
                diff_path,
                heatmap_path,
                comp_result["total_pixels"],
                comp_result["changed_pixels"],
                comp_result["difference_percentage"],
                comp_result["ssim_score"],
                comp_result["status"],
                cap_result.get("browser_info", "Chrome Headless"),
                json.dumps(dom_defects)
            )
        )
        test_id = cursor.lastrowid

        # Insert defects
        for d in all_defects:
            cursor.execute(
                """INSERT INTO detected_defects 
                   (test_execution_id, defect_type, description, x, y, width, height, severity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (test_id, d["defect_type"], d["description"], d.get("x", 0), d.get("y", 0), d.get("width", 0), d.get("height", 0), d.get("severity", "MEDIUM"))
            )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "test_id": test_id,
            "status": comp_result["status"],
            "difference_percentage": comp_result["difference_percentage"],
            "threshold": threshold,
            "ssim_score": comp_result["ssim_score"],
            "changed_pixels": comp_result["changed_pixels"],
            "total_pixels": comp_result["total_pixels"],
            "defect_count": len(all_defects),
            "screenshot_path": screenshot_path,
            "diff_path": diff_path,
            "heatmap_path": heatmap_path
        }

    @classmethod
    def run_manual_image_comparison(
        cls,
        application_id: int,
        baseline_file,
        current_file,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Processes two directly uploaded image files (PNG/JPEG) without launching a browser.
        Executes OpenCV dimension alignment, pixel diff, contour extraction, and heatmap rendering.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        Config.init_directories()

        base_path = str(Config.BASELINES_DIR / f"manual_base_app{application_id}_{timestamp}.png")
        curr_path = str(Config.SCREENSHOTS_DIR / f"manual_curr_app{application_id}_{timestamp}.png")

        baseline_file.save(base_path)
        current_file.save(curr_path)

        try:
            base_img = ImageProcessor.load_image(base_path)
            curr_img = ImageProcessor.load_image(curr_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to decode uploaded images: {str(e)}"}

        h, w = curr_img.shape[:2]
        viewport_str = f"{w}x{h}"

        # Computer Vision comparison
        comparator = VisualComparator()
        comp_result = comparator.compare(
            baseline_img=base_img,
            current_img=curr_img,
            acceptable_threshold_percent=threshold
        )

        diff_path = str(Config.DIFFS_DIR / f"manual_diff_app{application_id}_{timestamp}.png")
        heatmap_path = str(Config.HEATMAPS_DIR / f"manual_heatmap_app{application_id}_{timestamp}.png")

        ImageProcessor.save_image(comp_result["diff_overlay"], diff_path)
        heatmap_img = HeatmapGenerator.generate_heatmap(
            gray_diff=comp_result["gray_diff"],
            current_img=curr_img
        )
        ImageProcessor.save_image(heatmap_img, heatmap_path)

        # Record in SQLite database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create baseline entry for manual run
        cursor.execute(
            """INSERT INTO baselines (application_id, name, page_url, viewport, width, height, file_path, is_approved)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (application_id, f"Uploaded Manual Baseline ({timestamp})", "manual://uploaded", viewport_str, w, h, base_path)
        )
        baseline_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO test_executions 
               (application_id, baseline_id, test_url, viewport, threshold, screenshot_path, diff_path, heatmap_path,
                total_pixels, changed_pixels, difference_percentage, ssim_score, status, browser_info, dom_changes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Manual File Upload Engine', '[]')""",
            (
                application_id,
                baseline_id,
                "manual://uploaded",
                viewport_str,
                threshold,
                curr_path,
                diff_path,
                heatmap_path,
                comp_result["total_pixels"],
                comp_result["changed_pixels"],
                comp_result["difference_percentage"],
                comp_result["ssim_score"],
                comp_result["status"]
            )
        )
        test_id = cursor.lastrowid

        # Insert detected visual defects
        for box in comp_result["bounding_boxes"]:
            cursor.execute(
                """INSERT INTO detected_defects 
                   (test_execution_id, defect_type, description, x, y, width, height, severity)
                   VALUES (?, 'visual_difference', ?, ?, ?, ?, ?, ?)""",
                (test_id, f"Pixel deviation region ({box['width']}x{box['height']} px)", box["x"], box["y"], box["width"], box["height"], "HIGH" if comp_result["status"] == "FAIL" else "LOW")
            )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "test_id": test_id,
            "status": comp_result["status"],
            "difference_percentage": comp_result["difference_percentage"],
            "threshold": threshold,
            "ssim_score": comp_result["ssim_score"],
            "changed_pixels": comp_result["changed_pixels"],
            "total_pixels": comp_result["total_pixels"],
            "defect_count": len(comp_result["bounding_boxes"]),
            "screenshot_path": curr_path,
            "diff_path": diff_path,
            "heatmap_path": heatmap_path
        }

