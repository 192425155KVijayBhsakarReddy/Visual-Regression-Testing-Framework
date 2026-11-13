import pytest
import os
from visual_regression.app import create_app
from visual_regression.config import Config
from visual_regression.database import init_db, get_db_connection
from visual_regression.reports.report_generator import ReportGenerator

@pytest.fixture
def client(tmp_path):
    # Set temporary database path for testing
    test_db = str(tmp_path / "test_vr.db")
    Config.DATABASE_PATH = test_db
    Config.STORAGE_DIR = tmp_path / "storage"
    Config.BASELINES_DIR = Config.STORAGE_DIR / "baselines"
    Config.SCREENSHOTS_DIR = Config.STORAGE_DIR / "screenshots"
    Config.DIFFS_DIR = Config.STORAGE_DIR / "diffs"
    Config.HEATMAPS_DIR = Config.STORAGE_DIR / "heatmaps"
    Config.REPORTS_DIR = Config.STORAGE_DIR / "reports"
    Config.init_directories()

    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

def test_database_initialization(client):
    """Verify that all required tables and indexes are initialized."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "applications" in tables
    assert "baselines" in tables
    assert "test_executions" in tables
    assert "detected_defects" in tables

def test_dashboard_route_empty_state(client):
    """Dashboard loads properly with empty state."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Testing Dashboard" in response.data
    assert b"No test executions recorded yet" in response.data

def test_application_crud(client):
    """Test creating and retrieving an application."""
    # 1. Add application
    add_resp = client.post("/applications/add", data={
        "name": "Integration Test App",
        "url": "http://127.0.0.1:5001",
        "description": "Test App Description",
        "viewport": "desktop",
        "threshold": "0.5"
    }, follow_redirects=True)
    assert add_resp.status_code == 200
    assert b"Integration Test App" in add_resp.data

    # 2. Verify in DB
    conn = get_db_connection()
    app = conn.execute("SELECT * FROM applications WHERE name = 'Integration Test App'").fetchone()
    conn.close()
    assert app is not None
    assert app["url"] == "http://127.0.0.1:5001"

def test_report_generation(client):
    """Test generation of HTML, JSON, and CSV reports for a test execution."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO applications (name, url) VALUES ('Report App', 'http://localhost')")
    app_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO test_executions 
        (application_id, test_url, viewport, threshold, screenshot_path, status, total_pixels, changed_pixels, difference_percentage)
        VALUES (?, 'http://localhost', '1366x768', 0.5, 'dummy.png', 'PASS', 1000000, 0, 0.0)
    """, (app_id,))
    test_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # 1. HTML Report View
    html_resp = client.get(f"/reports/view/{test_id}")
    assert html_resp.status_code == 200
    assert b"Visual Regression Testing Report" in html_resp.data

    # 2. JSON Report
    json_resp = client.get(f"/reports/download/{test_id}?format=json")
    assert json_resp.status_code == 200
    assert b"difference_percentage" in json_resp.data

    # 3. CSV Report
    csv_resp = client.get(f"/reports/download/{test_id}?format=csv")
    assert csv_resp.status_code == 200
    assert b"Test ID,Application" in csv_resp.data

