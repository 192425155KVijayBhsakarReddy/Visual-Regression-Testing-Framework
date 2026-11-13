from flask import Blueprint, render_template, request, Response, send_file, flash, redirect, url_for
from visual_regression.database import get_db_connection
from visual_regression.reports.report_generator import ReportGenerator

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

@reports_bp.route("/")
def list_reports():
    conn = get_db_connection()
    reports = conn.execute("""
        SELECT t.*, a.name as application_name
        FROM test_executions t
        JOIN applications a ON t.application_id = a.id
        ORDER BY t.executed_at DESC
    """).fetchall()
    conn.close()
    return render_template("reports.html", active_page="reports", reports=[dict(r) for r in reports])

@reports_bp.route("/view/<int:test_id>")
def view_html_report(test_id):
    html_content = ReportGenerator.generate_html_report(test_id)
    return Response(html_content, mimetype="text/html")

@reports_bp.route("/download/<int:test_id>")
def download_report(test_id):
    fmt = request.args.get("format", "html").lower()
    if fmt == "json":
        json_content = ReportGenerator.generate_json_report(test_id)
        return Response(
            json_content,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename=report_test_{test_id}.json"}
        )
    elif fmt == "csv":
        csv_content = ReportGenerator.generate_csv_summary(test_id)
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=summary_test_{test_id}.csv"}
        )
    else:
        html_content = ReportGenerator.generate_html_report(test_id)
        return Response(
            html_content,
            mimetype="text/html",
            headers={"Content-Disposition": f"attachment;filename=report_test_{test_id}.html"}
        )

