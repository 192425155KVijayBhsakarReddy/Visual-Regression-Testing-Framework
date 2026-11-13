from flask import Blueprint, render_template, request, redirect, url_for, flash
from visual_regression.database import get_db_connection

applications_bp = Blueprint("applications", __name__, url_prefix="/applications")

@applications_bp.route("/")
def list_applications():
    conn = get_db_connection()
    apps = conn.execute("""
        SELECT a.*, COUNT(b.id) as baseline_count
        FROM applications a
        LEFT JOIN baselines b ON a.id = b.application_id
        GROUP BY a.id
        ORDER BY a.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("applications.html", active_page="applications", applications=[dict(a) for a in apps])

@applications_bp.route("/add", methods=["POST"])
def add_application():
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    description = request.form.get("description", "").strip()
    viewport = request.form.get("viewport", "desktop")
    threshold = float(request.form.get("threshold", 0.5))

    if not name or not url:
        flash("Application name and URL are mandatory.", "error")
        return redirect(url_for("applications.list_applications"))

    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO applications (name, url, description, default_viewport, default_threshold)
               VALUES (?, ?, ?, ?, ?)""",
            (name, url, description, viewport, threshold)
        )
        conn.commit()
        flash(f"Application '{name}' added successfully.", "success")
    except Exception as e:
        flash(f"Error adding application: {str(e)}", "error")
    finally:
        conn.close()

    return redirect(url_for("applications.list_applications"))

@applications_bp.route("/delete/<int:app_id>", methods=["POST"])
def delete_application(app_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()
        flash("Application and associated data deleted.", "success")
    except Exception as e:
        flash(f"Error deleting application: {str(e)}", "error")
    finally:
        conn.close()
    return redirect(url_for("applications.list_applications"))

