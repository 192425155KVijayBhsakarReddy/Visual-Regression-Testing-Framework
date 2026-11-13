import os
import sys
import argparse
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visual_regression.config import Config
from visual_regression.database import init_db, get_db_connection
from visual_regression.services.baseline_service import BaselineService
from visual_regression.services.test_service import TestService
from visual_regression.reports.report_generator import ReportGenerator

def main():
    parser = argparse.ArgumentParser(description="Visual Regression CI/CD Automated CLI Runner")
    parser.add_argument("--app-name", default="CI Target App", help="Name of application")
    parser.add_argument("--app-url", required=True, help="URL to test")
    parser.add_argument("--viewport", default="desktop", help="desktop | laptop | tablet | mobile")
    parser.add_argument("--threshold", type=float, default=0.5, help="Acceptable pixel difference threshold in percentage")
    parser.add_argument("--output-dir", default="ci_reports", help="Directory to save generated artifacts")
    parser.add_argument("--auto-baseline-if-missing", action="store_true", default=True, help="Automatically capture initial baseline if none exists")

    args = parser.parse_args()

    # 1. Initialize environment
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure application is registered
    app = cursor.execute("SELECT * FROM applications WHERE name = ? OR url = ?", (args.app_name, args.app_url)).fetchone()
    if not app:
        cursor.execute(
            "INSERT INTO applications (name, url, default_viewport, default_threshold) VALUES (?, ?, ?, ?)",
            (args.app_name, args.app_url, args.viewport, args.threshold)
        )
        conn.commit()
        app_id = cursor.lastrowid
    else:
        app_id = app["id"]

    vp = Config.SUPPORTED_VIEWPORTS.get(args.viewport, {"width": 1366, "height": 768})
    viewport_str = f"{vp['width']}x{vp['height']}"

    # Check for existing baseline - match by application and viewport
    baseline = cursor.execute(
        "SELECT * FROM baselines WHERE application_id = ? AND viewport = ? ORDER BY id ASC LIMIT 1",
        (app_id, viewport_str)
    ).fetchone()

    if not baseline and args.auto_baseline_if_missing:
        print(f"[CI Runner] No approved baseline found for {args.app_url} ({viewport_str}). Capturing initial baseline...")
        base_res = BaselineService.capture_and_save_baseline(
            application_id=app_id,
            name=f"{args.app_name} Initial Baseline",
            page_url=args.app_url,
            viewport_key=args.viewport
        )
        if not base_res["success"]:
            print(f"[CI Runner] ERROR: Failed to capture initial baseline: {base_res.get('error')}")
            sys.exit(1)
        baseline_id = base_res["baseline_id"]
        print(f"[CI Runner] Initial baseline #{baseline_id} recorded successfully.")
    elif baseline:
        baseline_id = baseline["id"]
    else:
        print(f"[CI Runner] ERROR: No baseline exists for {args.app_url}. Run baseline capture first.")
        sys.exit(1)

    conn.close()

    # 2. Execute Visual Regression Comparison
    print(f"[CI Runner] Launching test against {args.app_url} (Threshold: {args.threshold}%)...")
    result = TestService.run_test(
        application_id=app_id,
        test_url=args.app_url,
        viewport_key=args.viewport,
        baseline_id=baseline_id,
        custom_threshold=args.threshold,
        headless=True
    )

    if not result["success"]:
        print(f"[CI Runner] Test execution failed with error: {result.get('error')}")
        sys.exit(1)

    test_id = result["test_id"]
    status = result["status"]
    diff_percent = result["difference_percentage"]

    # 3. Output reports to artifact directory
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_report = ReportGenerator.generate_html_report(test_id)
    with open(out_dir / f"report_test_{test_id}.html", "w", encoding="utf-8") as f:
        f.write(html_report)

    json_report = ReportGenerator.generate_json_report(test_id)
    with open(out_dir / f"report_test_{test_id}.json", "w", encoding="utf-8") as f:
        f.write(json_report)

    csv_report = ReportGenerator.generate_csv_summary(test_id)
    with open(out_dir / f"summary_test_{test_id}.csv", "w", encoding="utf-8") as f:
        f.write(csv_report)

    print("==================================================")
    print(f"VISUAL REGRESSION TEST RESULT: {status}")
    print(f"Test Execution ID:      #{test_id}")
    print(f"Measured Difference:    {diff_percent}%")
    print(f"Allowed Threshold:      {args.threshold}%")
    print(f"Structural Similarity:  {result.get('ssim_score')}")
    print(f"Defects Flagged:        {result.get('defect_count')}")
    print(f"HTML Report Generated:  {out_dir / f'report_test_{test_id}.html'}")
    print("==================================================")

    if status == "FAIL":
        print("[CI Runner] FAILURE: Visual divergence exceeded acceptable threshold!")
        sys.exit(1)
    else:
        print("[CI Runner] SUCCESS: Visual verification passed within threshold.")
        sys.exit(0)

if __name__ == "__main__":
    main()
