from flask import Flask, render_template, request

sample_app = Flask(__name__)

# Simulated in-memory flag or query param to easily toggle visual regression defects
@sample_app.route("/")
def index():
    # If mode=regressed or modified, apply deliberate visual changes
    regression_mode = request.args.get("mode", "normal") == "regressed"
    return render_template("sample_index.html", regressed=regression_mode)

@sample_app.route("/login")
def login():
    regression_mode = request.args.get("mode", "normal") == "regressed"
    return render_template("sample_login.html", regressed=regression_mode)

@sample_app.route("/pricing")
def pricing():
    regression_mode = request.args.get("mode", "normal") == "regressed"
    return render_template("sample_pricing.html", regressed=regression_mode)

@sample_app.route("/analytics")
def analytics():
    regression_mode = request.args.get("mode", "normal") == "regressed"
    return render_template("sample_analytics.html", regressed=regression_mode)

if __name__ == "__main__":
    sample_app.run(host="0.0.0.0", port=5001, debug=True)

