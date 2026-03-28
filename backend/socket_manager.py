import json
import asyncio
from typing import List
from fastapi import WebSocket
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

def broadcast_log(sender: str, message: str, event_type: str = "system"):
    """Utility to broadcast a structured log to all connected websocket clients."""
    print(f"[{sender}] {message}")
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    payload = {
        "type": event_type,
        "sender": sender,
        "message": message,
        "timestamp": timestamp
    }
    
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast(json.dumps(payload)))
    except RuntimeError:
        pass
