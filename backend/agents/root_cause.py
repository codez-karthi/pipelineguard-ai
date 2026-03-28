import os
import json
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from socket_manager import broadcast_log

load_dotenv()

PROMPT_TEMPLATE = """
You are an expert Data Engineer AI. Analyze the following data pipeline error log and determine the root cause.
Classify the cause_type as exactly one of: schema_drift, data_quality, or timeout.

Log Data:
{log_data}

Return ONLY a valid JSON object with the following schema, and no other text:
{{
  "root_cause": "brief explanation",
  "cause_type": "schema_drift | data_quality | timeout",
  "confidence": 0.0 to 1.0,
  "recommended_action": "what should be done to fix it",
  "business_impact": "high/medium/low based on pipeline context"
}}
"""

def mock_root_cause_analysis(issue: dict) -> dict:
    error_msg = str(issue.get("error", "")).lower()
    if "keyerror" in error_msg or "schema" in error_msg or "column" in error_msg and "null" not in error_msg:
         return {
            "root_cause": "Missing column in source data",
            "cause_type": "schema_drift",
            "confidence": 0.95,
            "recommended_action": "Update column mapping to ignore missing column or set default",
            "business_impact": "high"
        }
    elif "dataquality" in error_msg or "null" in error_msg:
        return {
            "root_cause": "Null values found in required column",
            "cause_type": "data_quality",
            "confidence": 0.90,
            "recommended_action": "Filter or quarantine bad rows containing nulls",
            "business_impact": "medium"
        }
    elif "timeout" in error_msg:
        return {
            "root_cause": "Upstream API connection timed out",
            "cause_type": "timeout",
            "confidence": 0.85,
            "recommended_action": "Retry request with smaller dynamic partitioning",
            "business_impact": "low"
        }
    return {
        "root_cause": "Unknown error",
        "cause_type": "timeout",
        "confidence": 0.5,
        "recommended_action": "Manual inspection required",
        "business_impact": "high"
    }

def analyze_issue(issue: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    pipeline_id = issue.get('pipeline', 'unknown')
    
    broadcast_log("RootCause", f"Analyzing error signature for {pipeline_id}...", "root_cause")
    time.sleep(1)
    
    if api_key and api_key != "your_api_key_here":
        try:
            broadcast_log("RootCause", "Sending telemetry to Gemini AI for reasoning...", "root_cause")
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=api_key)
            prompt = PROMPT_TEMPLATE.format(log_data=json.dumps(issue))
            response = llm.invoke(prompt)
            content = response.content
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                return json.loads(content[start_idx:end_idx])
        except Exception as e:
            broadcast_log("RootCause", f"AI Analysis failed: {e}. Executing rule-based heuristics.", "root_cause")
    else:
        broadcast_log("RootCause", "No API key found. Executing rule-based heuristics.", "root_cause")
            
    return mock_root_cause_analysis(issue)

def root_cause_agent(state: dict) -> dict:
    broadcast_log("RootCause", "Initiating Root Cause Diagnostics...", "root_cause")
    time.sleep(2) # Artificial delay
    
    issues = state.get("pipeline_issues", [])
    diagnoses = []
    
    for issue in issues:
        diagnosis = analyze_issue(issue)
        cause_type = diagnosis.get('cause_type')
        root_cause = diagnosis.get('root_cause')
        
        broadcast_log("RootCause", f"[{issue.get('pipeline')}] Classified anomaly as: {cause_type}", "root_cause")
        time.sleep(1)
        broadcast_log("RootCause", f"[{issue.get('pipeline')}] Root cause identified: {root_cause}", "root_cause")
        
        merged = {**issue, "diagnosis": diagnosis}
        diagnoses.append(merged)
        
    return {"pipeline_issues": diagnoses}
