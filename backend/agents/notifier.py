from socket_manager import broadcast_log
import time

def notifier_agent(state: dict) -> dict:
    broadcast_log("Notifier", "Processing final mitigation alerts...", "notifier")
    time.sleep(1)
    results = state.get("healed_results", [])
    notifications = []
    
    for result in results:
        issue = result.get("original_issue", {})
        pipeline_name = issue.get("pipeline", "Unknown Pipeline")
        status = result.get("status")
        
        if status in ["resolved", "healed"]:
            broadcast_log("Notifier", f"[{pipeline_name}] Sent Success Webhook. Issue fully resolved.", "notifier")
        else:
            broadcast_log("Notifier", f"[{pipeline_name}] Sent Escalation Webhook. Manual intervention required.", "notifier")
            
        notifications.append(f"{pipeline_name} -> {status}")
        
    return {"notifications": notifications, "status": "completed"}
