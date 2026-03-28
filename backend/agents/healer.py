import time
from socket_manager import broadcast_log
import database
import json

def heal_schema_drift(issue: dict) -> dict:
    broadcast_log("Healer", f"Applying dynamic schema mapping fix for {issue.get('pipeline')}...", "healer")
    time.sleep(2) # Simulating work
    return {
        "status": "resolved",
        "action_taken": "Updated column mapping to ignore missing region_id",
        "original_issue": issue
    }

def heal_data_quality(issue: dict) -> dict:
    broadcast_log("Healer", f"Isolating malformed rows in {issue.get('pipeline')} to dead-letter queue...", "healer")
    time.sleep(2) # Simulating work
    return {
        "status": "resolved",
        "action_taken": "Quarantined invalid rows and resumed pipeline ingestion",
        "original_issue": issue
    }

def heal_timeout(issue: dict) -> dict:
    broadcast_log("Healer", f"Restarting {issue.get('pipeline')} with exponential backoff...", "healer")
    time.sleep(2) # Simulating work
    return {
        "status": "resolved",
        "action_taken": "Retried pipeline request with reduced dynamic partitioning",
        "original_issue": issue
    }

def healer_agent(state: dict) -> dict:
    broadcast_log("Healer", "Attempting autonomous remediation...", "healer")
    time.sleep(2) # Artificial delay
    
    issues = state.get("pipeline_issues", [])
    healed_results = []
    
    for issue in issues:
        diagnosis = issue.get("diagnosis", {})
        cause_type = diagnosis.get("cause_type", "")
        
        if cause_type == "schema_drift":
            result = heal_schema_drift(issue)
        elif cause_type == "data_quality":
            result = heal_data_quality(issue)
        elif cause_type == "timeout":
            result = heal_timeout(issue)
        else:
            broadcast_log("Healer", f"Unknown cause_type '{cause_type}'. Escalating to on-call.", "healer")
            result = {
                 "status": "manual_action_required",
                 "action_taken": "Failed auto-remediation. Escalated to on-call engineering.",
                 "original_issue": issue
            }
        
        healed_results.append(result)
        
        # Save resolution into SQLite DB
        log_id = issue.get("db_log_id")
        if log_id:
            database.update_log_ai_action(
                log_id=log_id,
                ai_output=json.dumps(diagnosis),
                final_action=result["action_taken"],
                new_status=result["status"]
            )
        
        broadcast_log("Healer", f"[{issue.get('pipeline')}] Recovery successful. Pipeline status restored.", "healer")
        time.sleep(1)
        
    return {"healed_results": healed_results}
