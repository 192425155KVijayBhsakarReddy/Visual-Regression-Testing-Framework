import os
import json
import csv
from io import StringIO
from datetime import datetime
from typing import Dict, Any
from visual_regression.database import get_db_connection

class ReportGenerator:
    """Generates standalone HTML, structured JSON, and CSV test execution reports."""

    @classmethod
    def get_full_test_data(cls, test_id: int) -> Dict[str, Any]:
        conn = get_db_connection()
        test = conn.execute(
            """SELECT t.*, a.name as application_name, a.url as application_root_url,
                      b.name as baseline_name, b.file_path as baseline_file_path
               FROM test_executions t
               JOIN applications a ON t.application_id = a.id
               LEFT JOIN baselines b ON t.baseline_id = b.id
               WHERE t.id = ?""",
            (test_id,)
        ).fetchone()

        if not test:
            conn.close()
            return {}

        defects = conn.execute(
            "SELECT * FROM detected_defects WHERE test_execution_id = ? ORDER BY severity DESC",
            (test_id,)
        ).fetchall()
        conn.close()

        data = dict(test)
        data["defects"] = [dict(d) for d in defects]
        return data

    @classmethod
    def generate_html_report(cls, test_id: int) -> str:
        data = cls.get_full_test_data(test_id)
        if not data:
            return "<html><body><h1>Test Execution Not Found</h1></body></html>"

        status_class = "pass" if data["status"] == "PASS" else ("fail" if data["status"] == "FAIL" else "error")
        status_badge = f'<span class="badge {status_class}">{data["status"]}</span>'

        defects_rows = ""
        for d in data.get("defects", []):
            defects_rows += f"""
            <tr>
                <td><span class="badge badge-sm badge-secondary">{d['defect_type']}</span></td>
                <td>{d['description']}</td>
                <td>{d['x']},{d['y']} ({d['width']}x{d['height']})</td>
                <td><span class="badge badge-sm {d['severity'].lower()}">{d['severity']}</span></td>
            </tr>
            """

        if not defects_rows:
            defects_rows = "<tr><td colspan='4' class='text-center text-muted'>No defects detected. Visual layout matches baseline.</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visual Regression Report - Test #{data['id']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
        .header {{ background: #0f172a; color: white; padding: 24px 32px; border-radius: 8px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
        .header h1 {{ margin: 0; font-size: 22px; font-weight: 600; letter-spacing: -0.5px; }}
        .badge {{ padding: 6px 14px; border-radius: 4px; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .pass {{ background: #10b981; color: white; }}
        .fail {{ background: #ef4444; color: white; }}
        .error {{ background: #f59e0b; color: white; }}
        .low {{ background: #94a3b8; color: white; }}
        .medium {{ background: #f59e0b; color: white; }}
        .high {{ background: #ef4444; color: white; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .card-label {{ font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }}
        .card-value {{ font-size: 20px; font-weight: 700; color: #0f172a; }}
        .images-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; margin-bottom: 28px; }}
        .img-card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }}
        .img-card-header {{ background: #f1f5f9; padding: 10px 16px; font-weight: 600; font-size: 14px; border-bottom: 1px solid #e2e8f0; }}
        .img-card img {{ width: 100%; height: auto; display: block; border-bottom: 1px solid #e2e8f0; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
        th {{ background: #f8fafc; font-weight: 600; color: #475569; }}
        .text-center {{ text-align: center; }}
        .text-muted {{ color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Visual Regression Testing Report</h1>
            <p style="margin: 4px 0 0 0; opacity: 0.8; font-size: 13px;">App: {data['application_name']} | Executed: {data['executed_at']}</p>
        </div>
        <div>{status_badge}</div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-label">Test URL</div>
            <div class="card-value" style="font-size: 14px; word-break: break-all;">{data['test_url']}</div>
        </div>
        <div class="card">
            <div class="card-label">Viewport</div>
            <div class="card-value">{data['viewport']}</div>
        </div>
        <div class="card">
            <div class="card-label">Pixel Difference</div>
            <div class="card-value" style="color: {'#ef4444' if data['difference_percentage'] > data['threshold'] else '#10b981'};">{data['difference_percentage']}%</div>
        </div>
        <div class="card">
            <div class="card-label">Configured Threshold</div>
            <div class="card-value">{data['threshold']}%</div>
        </div>
        <div class="card">
            <div class="card-label">SSIM Similarity</div>
            <div class="card-value">{data['ssim_score']}</div>
        </div>
        <div class="card">
            <div class="card-label">Changed / Total Pixels</div>
            <div class="card-value" style="font-size: 15px;">{data['changed_pixels']:,} / {data['total_pixels']:,}</div>
        </div>
    </div>

    <h2>Visual Evidence & Diagnostics</h2>
    <div class="images-grid">
        <div class="img-card">
            <div class="img-card-header">1. Approved Baseline Screenshot</div>
            <img src="/api/media?path={data.get('baseline_file_path', '')}" alt="Baseline" />
        </div>
        <div class="img-card">
            <div class="img-card-header">2. Current Run Screenshot</div>
            <img src="/api/media?path={data.get('screenshot_path', '')}" alt="Current" />
        </div>
        <div class="img-card">
            <div class="img-card-header">3. Difference Overlay (Red Highlighting)</div>
            <img src="/api/media?path={data.get('diff_path', '')}" alt="Difference Overlay" />
        </div>
        <div class="img-card">
            <div class="img-card-header">4. Difference Heatmap (Intensity Distribution)</div>
            <img src="/api/media?path={data.get('heatmap_path', '')}" alt="Heatmap" />
        </div>
    </div>

    <h2>Detected Layout & Visual Defects ({len(data.get('defects', []))})</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 150px;">Defect Type</th>
                <th>Description</th>
                <th style="width: 160px;">Coordinates</th>
                <th style="width: 100px;">Severity</th>
            </tr>
        </thead>
        <tbody>
            {defects_rows}
        </tbody>
    </table>
</body>
</html>
"""
        return html

    @classmethod
    def generate_json_report(cls, test_id: int) -> str:
        data = cls.get_full_test_data(test_id)
        return json.dumps(data, indent=2, default=str)

    @classmethod
    def generate_csv_summary(cls, test_id: int) -> str:
        data = cls.get_full_test_data(test_id)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Test ID", "Application", "Page URL", "Viewport", "Status", "Diff %", "Threshold %", "SSIM", "Changed Pixels", "Total Pixels", "Executed At"])
        writer.writerow([
            data.get("id"),
            data.get("application_name"),
            data.get("test_url"),
            data.get("viewport"),
            data.get("status"),
            data.get("difference_percentage"),
            data.get("threshold"),
            data.get("ssim_score"),
            data.get("changed_pixels"),
            data.get("total_pixels"),
            data.get("executed_at")
        ])
        return output.getvalue()

