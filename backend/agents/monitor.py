import json
import os
import glob
import time
from typing import Dict, Any, List
from socket_manager import broadcast_log
import database

MOCK_LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "mock_logs")

def read_pipeline_logs() -> List[Dict[str, Any]]:
    logs = []
    for filepath in glob.glob(os.path.join(MOCK_LOGS_DIR, "*.json")):
        try:
            with open(filepath, "r") as f:
                logs.append(json.load(f))
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
    return logs

def detect_new_anomalies(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detects changes or new anomalies against the SQLite database."""
    current_db_state = {row["pipeline_id"]: row for row in database.get_current_status()}
    issues = []
    
    for log in logs:
        pipeline_id = log.get("pipeline")
        status = log.get("status")
        rows_loaded = log.get("rows_loaded")
        error = log.get("error")
        run_time = log.get("run_time")
        
        # Check if rows < 500
        if rows_loaded is not None and rows_loaded < 500 and status != "failed":
            error = "LowRowCountAnomaly: Loaded rows < 50% of expected baseline"
            status = "failed"
            log["error"] = error
            log["status"] = status
            
        if status != "failed":
            continue
            
        # Is this a new issue?
        db_record = current_db_state.get(pipeline_id)
        is_new_timestamp = not db_record or db_record["timestamp"] != run_time
        is_new_failure = db_record and db_record["status"] != "failed"

        if is_new_timestamp or is_new_failure:
            # It's new!
            # Insert into database to track it
            log_id = database.add_log(
                pipeline_id=pipeline_id,
                status="failed",
                rows_loaded=rows_loaded,
                error=error,
                raw_json=json.dumps(log)
            )
            log["db_log_id"] = log_id
            issues.append(log)
            
    return issues

def monitor_agent(state: dict) -> dict:
    broadcast_log("Monitor", "Scanning logs...", "monitor")
    time.sleep(2) # Artificial realism delay
    
    logs = read_pipeline_logs()
    issues = detect_new_anomalies(logs)
    
    if issues:
        broadcast_log("Monitor", f"Detected {len(issues)} new anomaly(ies). Forwarding to AI Diagnostics.", "monitor")
        return {"pipeline_issues": issues, "status": "issues_detected"}
    
    return {"pipeline_issues": [], "status": "ok"}
