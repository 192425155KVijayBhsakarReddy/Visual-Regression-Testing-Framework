import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from visual_regression.config import Config
from visual_regression.database import get_db_connection
from visual_regression.capture.screenshot_capture import ScreenshotCapture
from visual_regression.vision.image_processor import ImageProcessor

logger = logging.getLogger("BaselineService")

class BaselineService:
    """Manages creation, retrieval, validation, and user-approved updates of baseline reference screenshots."""

    @classmethod
    def get_baseline_by_id(cls, baseline_id: int) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        row = conn.execute("SELECT * FROM baselines WHERE id = ?", (baseline_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @classmethod
    def get_baseline_for_page(cls, application_id: int, page_url: str, viewport: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT * FROM baselines WHERE application_id = ? AND page_url = ? AND viewport = ?",
            (application_id, page_url, viewport)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    @classmethod
    def list_baselines(cls, application_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        if application_id:
            rows = conn.execute(
                """SELECT b.*, a.name as application_name 
                   FROM baselines b 
                   JOIN applications a ON b.application_id = a.id 
                   WHERE b.application_id = ? 
                   ORDER BY b.created_at DESC""",
                (application_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT b.*, a.name as application_name 
                   FROM baselines b 
                   JOIN applications a ON b.application_id = a.id 
                   ORDER BY b.created_at DESC"""
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @classmethod
    def capture_and_save_baseline(
        cls,
        application_id: int,
        name: str,
        page_url: str,
        viewport_key: str = "desktop"
    ) -> Dict[str, Any]:
        """Captures page using Selenium and stores as approved baseline."""
        vp = Config.SUPPORTED_VIEWPORTS.get(viewport_key, {"width": 1366, "height": 768})
        viewport_str = f"{vp['width']}x{vp['height']}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"baseline_app{application_id}_{viewport_str}_{timestamp}.png"
        file_path = str(Config.BASELINES_DIR / filename)

        # 1. Capture screen
        cap_result = ScreenshotCapture.capture(
            url=page_url,
            output_path=file_path,
            viewport_key=viewport_key,
            headless=Config.HEADLESS
        )

        if not cap_result["success"]:
            return {"success": False, "error": cap_result.get("error", "Capture failed")}

        dom_json = json.dumps(cap_result.get("dom_elements", []))

        # 2. Store or update record in database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if existing baseline for this page/viewport
        existing = cursor.execute(
            "SELECT id, file_path FROM baselines WHERE application_id = ? AND page_url = ? AND viewport = ?",
            (application_id, page_url, viewport_str)
        ).fetchone()

        if existing:
            # Explicit update
            cursor.execute(
                """UPDATE baselines 
                   SET name = ?, file_path = ?, width = ?, height = ?, dom_snapshot = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (name, file_path, vp["width"], vp["height"], dom_json, existing["id"])
            )
            baseline_id = existing["id"]
        else:
            cursor.execute(
                """INSERT INTO baselines (application_id, name, page_url, viewport, width, height, file_path, dom_snapshot, is_approved)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (application_id, name, page_url, viewport_str, vp["width"], vp["height"], file_path, dom_json)
            )
            baseline_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return {
            "success": True,
            "baseline_id": baseline_id,
            "file_path": file_path,
            "viewport": viewport_str,
            "width": vp["width"],
            "height": vp["height"]
        }

    @classmethod
    def upload_baseline(
        cls,
        application_id: int,
        name: str,
        page_url: str,
        viewport_key: str,
        uploaded_file
    ) -> Dict[str, Any]:
        """Allows direct user upload of an approved baseline image file."""
        vp = Config.SUPPORTED_VIEWPORTS.get(viewport_key, {"width": 1366, "height": 768})
        viewport_str = f"{vp['width']}x{vp['height']}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"uploaded_baseline_app{application_id}_{viewport_str}_{timestamp}.png"
        file_path = str(Config.BASELINES_DIR / filename)

        uploaded_file.save(file_path)

        # Validate that image can be read by OpenCV
        try:
            img = ImageProcessor.load_image(file_path)
            h, w = img.shape[:2]
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return {"success": False, "error": f"Invalid image file: {str(e)}"}

        conn = get_db_connection()
        cursor = conn.cursor()

        existing = cursor.execute(
            "SELECT id FROM baselines WHERE application_id = ? AND page_url = ? AND viewport = ?",
            (application_id, page_url, viewport_str)
        ).fetchone()

        if existing:
            cursor.execute(
                """UPDATE baselines 
                   SET name = ?, file_path = ?, width = ?, height = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (name, file_path, w, h, existing["id"])
            )
            baseline_id = existing["id"]
        else:
            cursor.execute(
                """INSERT INTO baselines (application_id, name, page_url, viewport, width, height, file_path, is_approved)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (application_id, name, page_url, viewport_str, w, h, file_path)
            )
            baseline_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return {"success": True, "baseline_id": baseline_id, "file_path": file_path}

    @classmethod
    def approve_new_baseline_from_test(cls, test_id: int) -> Dict[str, Any]:
        """
        Explicit user action: replace baseline with current screenshot from a test execution.
        NEVER performed automatically on test failure.
        """
        conn = get_db_connection()
        test = conn.execute("SELECT * FROM test_executions WHERE id = ?", (test_id,)).fetchone()
        if not test:
            conn.close()
            return {"success": False, "error": "Test execution not found"}

        current_screenshot = test["screenshot_path"]
        if not os.path.exists(current_screenshot):
            conn.close()
            return {"success": False, "error": "Test screenshot file does not exist on disk"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_baseline_path = str(Config.BASELINES_DIR / f"approved_app{test['application_id']}_{timestamp}.png")
        shutil.copy2(current_screenshot, new_baseline_path)

        img = ImageProcessor.load_image(new_baseline_path)
        h, w = img.shape[:2]

        cursor = conn.cursor()
        if test["baseline_id"]:
            cursor.execute(
                """UPDATE baselines 
                   SET file_path = ?, width = ?, height = ?, updated_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (new_baseline_path, w, h, test["baseline_id"])
            )
        else:
            cursor.execute(
                """INSERT INTO baselines (application_id, name, page_url, viewport, width, height, file_path, is_approved)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (test["application_id"], f"Baseline from Test #{test_id}", test["test_url"], test["viewport"], w, h, new_baseline_path)
            )

        conn.commit()
        conn.close()
        return {"success": True, "message": "Baseline successfully updated from approved test screenshot"}

    @classmethod
    def delete_baseline(cls, baseline_id: int) -> bool:
        conn = get_db_connection()
        row = conn.execute("SELECT file_path FROM baselines WHERE id = ?", (baseline_id,)).fetchone()
        if row:
            if os.path.exists(row["file_path"]):
                try:
                    os.remove(row["file_path"])
                except Exception:
                    pass
            conn.execute("DELETE FROM baselines WHERE id = ?", (baseline_id,))
            conn.commit()
            conn.close()
            return True
        conn.close()
        return False

