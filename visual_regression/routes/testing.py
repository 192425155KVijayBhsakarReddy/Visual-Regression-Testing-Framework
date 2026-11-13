from flask import Blueprint, render_template, request, redirect, url_for, flash
from visual_regression.database import get_db_connection
from visual_regression.services.test_service import TestService

testing_bp = Blueprint("testing", __name__, url_prefix="/testing")

@testing_bp.route("/run", methods=["GET"])
def run_test_page():
    conn = get_db_connection()
    apps = conn.execute("SELECT * FROM applications ORDER BY name ASC").fetchall()
    baselines = conn.execute("""
        SELECT b.*, a.name as application_name 
        FROM baselines b 
        JOIN applications a ON b.application_id = a.id 
        ORDER BY b.created_at DESC
    """).fetchall()
    conn.close()

    selected_app_id = request.args.get("app_id", type=int)
    default_url = ""
    if selected_app_id:
        for a in apps:
            if a["id"] == selected_app_id:
                default_url = a["url"]
                break

    return render_template(
        "run_test.html",
        active_page="run_tests",
        applications=[dict(a) for a in apps],
        baselines=[dict(b) for b in baselines],
        selected_app_id=selected_app_id,
        default_url=default_url
    )

@testing_bp.route("/start", methods=["POST"])
def start_test():
    app_id = request.form.get("application_id", type=int)
    test_url = request.form.get("test_url", "").strip()
    viewport = request.form.get("viewport", "desktop")
    threshold = request.form.get("threshold", type=float)
    baseline_id = request.form.get("baseline_id", type=int) or None

    if not app_id or not test_url:
        flash("Application and Target URL are required.", "error")
        return redirect(url_for("testing.run_test_page"))

    result = TestService.run_test(
        application_id=app_id,
        test_url=test_url,
        viewport_key=viewport,
        baseline_id=baseline_id,
        custom_threshold=threshold
    )

    if not result["success"]:
        flash(f"Test failed to complete: {result.get('error')}", "error")
        return redirect(url_for("testing.run_test_page"))

    flash(f"Test #{result['test_id']} completed with status: {result['status']}", "success" if result["status"] == "PASS" else "error")
    return redirect(url_for("testing.comparison_page", test_id=result["test_id"]))

@testing_bp.route("/comparison/<int:test_id>")
def comparison_page(test_id):
    conn = get_db_connection()
    test = conn.execute("""
        SELECT t.*, a.name as application_name, b.name as baseline_name, b.file_path as baseline_file_path
        FROM test_executions t
        JOIN applications a ON t.application_id = a.id
        LEFT JOIN baselines b ON t.baseline_id = b.id
        WHERE t.id = ?
    """, (test_id,)).fetchone()

    if not test:
        conn.close()
        flash(f"Test execution #{test_id} not found.", "error")
        return redirect(url_for("testing.history_page"))

    defects = conn.execute("SELECT * FROM detected_defects WHERE test_execution_id = ? ORDER BY severity DESC", (test_id,)).fetchall()
    conn.close()

    return render_template(
        "comparison.html",
        active_page="comparison",
        test=dict(test),
        defects=[dict(d) for d in defects]
    )

@testing_bp.route("/upload-compare", methods=["GET"])
def manual_upload_page():
    conn = get_db_connection()
    apps = conn.execute("SELECT * FROM applications ORDER BY name ASC").fetchall()
    conn.close()
    return render_template(
        "manual_upload.html",
        active_page="manual_upload",
        applications=[dict(a) for a in apps]
    )

@testing_bp.route("/compare-upload", methods=["POST"])
def process_manual_upload():
    app_id = request.form.get("application_id", type=int)
    threshold = float(request.form.get("threshold", 0.5))
    base_file = request.files.get("baseline_image")
    curr_file = request.files.get("current_image")

    if not app_id or not base_file or not curr_file:
        flash("Application, Baseline Image, and Current Image are all required.", "error")
        return redirect(url_for("testing.manual_upload_page"))

    result = TestService.run_manual_image_comparison(
        application_id=app_id,
        baseline_file=base_file,
        current_file=curr_file,
        threshold=threshold
    )

    if not result["success"]:
        flash(f"Comparison failed: {result.get('error')}", "error")
        return redirect(url_for("testing.manual_upload_page"))

    flash(f"Comparison complete! Result: {result['status']} (Diff: {result['difference_percentage']}%)", "success" if result["status"] == "PASS" else "error")
    return redirect(url_for("testing.comparison_page", test_id=result["test_id"]))

@testing_bp.route("/history")
def history_page():
    app_id = request.args.get("app_id", "")
    status = request.args.get("status", "")
    search = request.args.get("search", "").strip()

    conn = get_db_connection()
    apps = conn.execute("SELECT * FROM applications ORDER BY name ASC").fetchall()

    query = """
        SELECT t.*, a.name as application_name
        FROM test_executions t
        JOIN applications a ON t.application_id = a.id
        WHERE 1=1
    """
    params = []

    if app_id:
        query += " AND t.application_id = ?"
        params.append(app_id)
    if status:
        query += " AND t.status = ?"
        params.append(status)
    if search:
        query += " AND (t.test_url LIKE ? OR t.id = ?)"
        params.extend([f"%{search}%", search])

    query += " ORDER BY t.executed_at DESC"
    history = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "history.html",
        active_page="history",
        history=[dict(h) for h in history],
        applications=[dict(a) for a in apps],
        selected_app=app_id,
        selected_status=status,
        search_query=search
    )

