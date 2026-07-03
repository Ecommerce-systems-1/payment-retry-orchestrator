import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pathlib

from app.database import (
    get_db_path, init_db, get_connection, insert_charge, get_charge,
    get_attempts, get_stats,
)
from app.models import ChargeRequest, ChargeResponse, ChargeStatusResponse, StatsResponse
from app.retry_orchestrator import RetryOrchestrator

orchestrator: RetryOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    db_path = get_db_path()
    init_db(db_path)
    orchestrator = RetryOrchestrator(db_path)
    await orchestrator.start()
    yield
    await orchestrator.stop()
    orchestrator = None


app = FastAPI(title="Payment Retry Orchestrator", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    depth = orchestrator.queue_depth() if orchestrator else 0
    return {"status": "ok", "queue_depth": depth}


@app.post("/api/charges", status_code=202, response_model=ChargeResponse)
async def create_charge(payload: ChargeRequest):
    if orchestrator is None:
        raise HTTPException(503, "Orchestrator not running")
    charge_id = f"CHG-{uuid.uuid4().hex[:10].upper()}"
    conn = get_connection(get_db_path())
    try:
        insert_charge(conn, charge_id, payload.amount, payload.currency,
                      payload.customer_id, payload.description, payload.max_retries)
        await orchestrator.enqueue(charge_id)
        return get_charge(conn, charge_id)
    finally:
        conn.close()


@app.get("/api/charges/{charge_id}", response_model=ChargeStatusResponse)
def charge_status(charge_id: str):
    conn = get_connection(get_db_path())
    try:
        charge = get_charge(conn, charge_id)
        if not charge:
            raise HTTPException(404, "Charge not found")
        return {**charge, "attempts": get_attempts(conn, charge_id)}
    finally:
        conn.close()


@app.get("/api/charges")
def list_charges(limit: int = 50):
    conn = get_connection(get_db_path())
    try:
        rows = conn.execute(
            "SELECT * FROM charges ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/stats", response_model=StatsResponse)
def stats():
    conn = get_connection(get_db_path())
    try:
        return get_stats(conn)
    finally:
        conn.close()


static_dir = pathlib.Path("/app/frontend/out")
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
