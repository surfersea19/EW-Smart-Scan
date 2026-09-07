import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.simulation_routes import router as simulation_router
from api.comparison_routes import router as comparison_router
from websocket.simulation_socket import router as ws_router, simulation_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(simulation_loop())
    yield
    task.cancel()


app = FastAPI(title="Smart EW Scan Scheduler", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation_router)
app.include_router(comparison_router)
app.include_router(ws_router)


@app.get("/")
def root():
    return {"status": "ok", "service": "smart-ew-scan-scheduler-backend"}
