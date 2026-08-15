import json
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws/bus-locations")
async def websocket_bus_locations(websocket: WebSocket):
    """
    Realtime WebSocket channel for broadcasting bus GPS locations to Student App and Admin Web.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                # Broadcast payload (vehicle_id, latitude, longitude, speed) to all connected clients
                await manager.broadcast(payload)
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
