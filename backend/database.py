import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "pipeline_history.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_id TEXT NOT NULL,
            status TEXT NOT NULL,
            rows_loaded INTEGER,
            error TEXT,
            timestamp TEXT NOT NULL,
            raw_json TEXT,
            ai_output TEXT,
            final_action TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_log(pipeline_id: str, status: str, rows_loaded: int, error: str, raw_json: str = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.utcnow().isoformat() + "Z"
    cursor.execute('''
        INSERT INTO history (pipeline_id, status, rows_loaded, error, timestamp, raw_json)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (pipeline_id, status, rows_loaded, error, timestamp, raw_json))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def update_log_ai_action(log_id: int, ai_output: str, final_action: str, new_status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE history 
        SET ai_output = ?, final_action = ?, status = ?
        WHERE id = ?
    ''', (ai_output, final_action, new_status, log_id))
    conn.commit()
    conn.close()

def get_current_status() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Get latest row for each pipeline
    cursor.execute('''
        SELECT *
        FROM history
        WHERE id IN (
            SELECT MAX(id)
            FROM history
            GROUP BY pipeline_id
        )
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_history() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM history ORDER BY id DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Initialize DB when module is imported
init_db()
