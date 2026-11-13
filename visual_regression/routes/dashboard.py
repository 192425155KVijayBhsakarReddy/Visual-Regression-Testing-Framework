from flask import Blueprint, render_template
from visual_regression.database import get_db_connection

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Aggregate statistics
    total_tests = cursor.execute("SELECT COUNT(*) FROM test_executions").fetchone()[0]
    passed_tests = cursor.execute("SELECT COUNT(*) FROM test_executions WHERE status = 'PASS'").fetchone()[0]
    failed_tests = cursor.execute("SELECT COUNT(*) FROM test_executions WHERE status = 'FAIL'").fetchone()[0]
    total_defects = cursor.execute("SELECT COUNT(*) FROM detected_defects").fetchone()[0]
    total_baselines = cursor.execute("SELECT COUNT(*) FROM baselines").fetchone()[0]
    total_apps = cursor.execute("SELECT COUNT(*) FROM applications").fetchone()[0]

    # Recent test runs
    recent_tests = cursor.execute("""
        SELECT t.*, a.name as application_name 
        FROM test_executions t 
        JOIN applications a ON t.application_id = a.id 
        ORDER BY t.executed_at DESC LIMIT 10
    """).fetchall()

    # Trend data (last 10 tests)
    trend_rows = cursor.execute("""
        SELECT id, difference_percentage, executed_at 
        FROM test_executions 
        ORDER BY executed_at ASC LIMIT 15
    """).fetchall()

    trend_labels = [f"#{r['id']}" for r in trend_rows]
    trend_data = [float(r["difference_percentage"]) for r in trend_rows]

    conn.close()

    stats = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "total_defects": total_defects,
        "total_baselines": total_baselines,
        "total_apps": total_apps
    }

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        stats=stats,
        recent_tests=[dict(t) for t in recent_tests],
        trend_labels=trend_labels,
        trend_data=trend_data
    )

