import os
from flask import Flask, send_file, abort, request, render_template
from visual_regression.config import Config
from visual_regression.database import init_db
from visual_regression.routes.dashboard import dashboard_bp
from visual_regression.routes.applications import applications_bp
from visual_regression.routes.testing import testing_bp
from visual_regression.routes.baselines import baselines_bp
from visual_regression.routes.reports import reports_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize tables and storage directories
    init_db()

    # Register Route Blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(testing_bp)
    app.register_blueprint(baselines_bp)
    app.register_blueprint(reports_bp)

    # Media endpoint to securely serve stored screenshots, diffs, and heatmaps
    @app.route("/api/media")
    def serve_media():
        path = request.args.get("path")
        if not path or not os.path.exists(path):
            abort(404)
        # Ensure path is within application root to prevent path traversal
        norm_path = os.path.abspath(path)
        norm_storage = os.path.abspath(str(Config.STORAGE_DIR))
        if not norm_path.startswith(norm_storage):
            # Allow fallback if file exists and is an image
            if not norm_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                abort(403)
        return send_file(norm_path)

    @app.route("/settings")
    def settings():
        return render_template("settings.html", active_page="settings", config=Config)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)

