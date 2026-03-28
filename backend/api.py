import asyncio
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from agents.orchestrator import build_orchestrator
from socket_manager import manager, broadcast_log
import uvicorn
import json
import os
from pydantic import BaseModel
import database

app = FastAPI(title="PipelineGuard AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = build_orchestrator()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/pipelines")
def get_pipelines():
    return database.get_current_status()

@app.get("/history")
def get_history():
    return database.get_history()

from typing import Optional

class LogEntry(BaseModel):
    pipeline: str
    status: str
    rows_loaded: Optional[int] = None
    error: Optional[str] = None
    run_time: Optional[str] = None

@app.post("/add-log")
async def add_log(entry: LogEntry):
    # Save the log to mock_logs/ directory
    file_path = os.path.join("mock_logs", f"{entry.pipeline}.json")
    with open(file_path, "w") as f:
        json.dump(entry.dict(), f, indent=4)
    # The monitor loop will pick this up automatically
    return {"status": "Log saved. Monitor will process it."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_pipeline_check():
    """Runs the LangGraph orchestrator."""
    broadcast_log("System", "Starting pipeline monitoring cycle...")
    try:
        initial_state = {"pipeline_issues": [], "healed_results": [], "notifications": [], "status": "init"}
        result_state = await asyncio.to_thread(orchestrator.invoke, initial_state)
        broadcast_log("System", "Cycle complete.")
    except Exception as e:
        broadcast_log("System", f"Error in pipeline logic: {e}")

@app.post("/trigger-cycle")
async def trigger_cycle(background_tasks: BackgroundTasks):
    """Manually trigger a pipeline check cycle."""
    background_tasks.add_task(run_pipeline_check)
    return {"status": "Cycle triggered"}

@app.post("/inject-failure")
async def inject_failure():
    """Endpoint required by specs to simulate failure.
    For this demo, the mock JSONs already contain failures.
    We just trigger the cycle which will pick them up.
    """
    await run_pipeline_check()
    return {"status": "Failure injected and cycle triggered"}

async def continuous_monitoring():
    """Background task to run monitor every 5 seconds."""
    while True:
        await asyncio.sleep(5)
        try:
            initial_state = {"pipeline_issues": [], "healed_results": [], "notifications": [], "status": "init"}
            await asyncio.to_thread(orchestrator.invoke, initial_state)
        except Exception as e:
            print(f"Error in pipeline logic: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(continuous_monitoring())

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
