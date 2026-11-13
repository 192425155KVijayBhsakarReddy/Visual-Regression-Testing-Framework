import sqlite3
import logging
from datetime import datetime
from visual_regression.config import Config

logger = logging.getLogger("Database")

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    Config.init_directories()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Applications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        url TEXT NOT NULL,
        description TEXT,
        default_viewport TEXT DEFAULT '1366x768',
        default_threshold REAL DEFAULT 0.5,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Baselines table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS baselines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        page_url TEXT NOT NULL,
        viewport TEXT NOT NULL,
        width INTEGER NOT NULL,
        height INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        dom_snapshot TEXT,
        is_approved INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE,
        UNIQUE(application_id, page_url, viewport)
    );
    """)

    # 3. Test Executions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        baseline_id INTEGER,
        test_url TEXT NOT NULL,
        viewport TEXT NOT NULL,
        threshold REAL NOT NULL,
        screenshot_path TEXT NOT NULL,
        diff_path TEXT,
        heatmap_path TEXT,
        total_pixels INTEGER DEFAULT 0,
        changed_pixels INTEGER DEFAULT 0,
        difference_percentage REAL DEFAULT 0.0,
        ssim_score REAL DEFAULT 1.0,
        status TEXT NOT NULL, -- 'PASS', 'FAIL', 'ERROR'
        error_message TEXT,
        browser_info TEXT,
        dom_changes TEXT,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE,
        FOREIGN KEY (baseline_id) REFERENCES baselines (id) ON DELETE SET NULL
    );
    """)

    # 4. Detected Defects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detected_defects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_execution_id INTEGER NOT NULL,
        defect_type TEXT NOT NULL, -- 'visual_difference', 'element_moved', 'element_missing', 'element_resized', 'css_modified'
        description TEXT NOT NULL,
        x INTEGER,
        y INTEGER,
        width INTEGER,
        height INTEGER,
        severity TEXT DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH'
        FOREIGN KEY (test_execution_id) REFERENCES test_executions (id) ON DELETE CASCADE
    );
    """)

    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_app ON test_executions(application_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_status ON test_executions(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_date ON test_executions(executed_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_baseline_app ON baselines(application_id);")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully at %s", Config.DATABASE_PATH)

