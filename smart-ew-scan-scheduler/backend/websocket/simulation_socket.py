import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.orchestrator import get_orchestrator

router = APIRouter()

TICK_INTERVAL_SECONDS = 0.4  # ~2.5 ticks/sec -- readable for a demo, not overwhelming

_connected: set[WebSocket] = set()


@router.websocket("/ws/simulation")
async def simulation_ws(websocket: WebSocket):
    await websocket.accept()
    _connected.add(websocket)
    try:
        while True:
            # Keep the connection alive; also allows the client to send
            # control pings if ever needed. Actual ticking happens in the
            # background loop below via broadcast().
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connected.discard(websocket)


async def broadcast(payload: dict) -> None:
    dead = []
    for ws in _connected:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connected.discard(ws)


async def simulation_loop():
    """
    Background task, started once at app startup. Only ticks the
    orchestrator forward when state.running is True, and only broadcasts
    when there's at least one connected client.
    """
    orch = get_orchestrator()
    while True:
        if orch.state.running:
            delta = orch.tick()
            if _connected:
                await broadcast(json.loads(delta.model_dump_json()))
        await asyncio.sleep(TICK_INTERVAL_SECONDS)
