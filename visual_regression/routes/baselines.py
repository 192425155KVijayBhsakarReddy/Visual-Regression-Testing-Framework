from flask import Blueprint, render_template, request, redirect, url_for, flash
from visual_regression.database import get_db_connection
from visual_regression.services.baseline_service import BaselineService

baselines_bp = Blueprint("baselines", __name__, url_prefix="/baselines")

@baselines_bp.route("/")
def list_baselines():
    conn = get_db_connection()
    apps = conn.execute("SELECT * FROM applications ORDER BY name ASC").fetchall()
    baselines = BaselineService.list_baselines()
    conn.close()
    return render_template(
        "baselines.html",
        active_page="baselines",
        baselines=baselines,
        applications=[dict(a) for a in apps]
    )

@baselines_bp.route("/capture", methods=["POST"])
def capture_baseline():
    app_id = request.form.get("application_id", type=int)
    name = request.form.get("name", "").strip()
    page_url = request.form.get("page_url", "").strip()
    viewport = request.form.get("viewport", "desktop")

    if not app_id or not name or not page_url:
        flash("Application, Baseline Name, and Page URL are required.", "error")
        return redirect(url_for("baselines.list_baselines"))

    res = BaselineService.capture_and_save_baseline(
        application_id=app_id,
        name=name,
        page_url=page_url,
        viewport_key=viewport
    )

    if res["success"]:
        flash(f"Baseline '{name}' successfully captured and saved.", "success")
    else:
        flash(f"Failed to capture baseline: {res.get('error')}", "error")

    return redirect(url_for("baselines.list_baselines"))

@baselines_bp.route("/upload", methods=["POST"])
def upload_baseline():
    app_id = request.form.get("application_id", type=int)
    name = request.form.get("name", "").strip()
    page_url = request.form.get("page_url", "").strip()
    viewport = request.form.get("viewport", "desktop")
    file = request.files.get("file")

    if not app_id or not name or not page_url or not file:
        flash("All fields including screenshot image file are required.", "error")
        return redirect(url_for("baselines.list_baselines"))

    res = BaselineService.upload_baseline(
        application_id=app_id,
        name=name,
        page_url=page_url,
        viewport_key=viewport,
        uploaded_file=file
    )

    if res["success"]:
        flash(f"Baseline '{name}' uploaded and approved.", "success")
    else:
        flash(f"Upload failed: {res.get('error')}", "error")

    return redirect(url_for("baselines.list_baselines"))

@baselines_bp.route("/approve-from-test/<int:test_id>", methods=["POST"])
def approve_from_test(test_id):
    res = BaselineService.approve_new_baseline_from_test(test_id)
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(res["error"], "error")
    return redirect(url_for("testing.comparison_page", test_id=test_id))

@baselines_bp.route("/delete/<int:baseline_id>", methods=["POST"])
def delete_baseline(baseline_id):
    if BaselineService.delete_baseline(baseline_id):
        flash("Baseline deleted successfully.", "success")
    else:
        flash("Could not delete baseline.", "error")
    return redirect(url_for("baselines.list_baselines"))

