import pytest
import asyncio
import tempfile, os
from unittest.mock import patch, AsyncMock
from app.database import init_db, get_connection, insert_charge, get_charge
from app.retry_orchestrator import RetryOrchestrator
from app.synthetic_processor import ProcessorResponse

@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)

@pytest.mark.asyncio
async def test_stop_drains_queue_within_timeout(tmp_db):
    success_resp = ProcessorResponse(True, "txn_abc_1234", None, None, 50)
    with patch("app.retry_orchestrator.process_payment", return_value=success_resp):
        orch = RetryOrchestrator(tmp_db)
        conn = get_connection(tmp_db)
        for i in range(3):
            insert_charge(conn, f"CHG-DRAIN-{i}", 10.0, "USD", "C1", None, 0)
        conn.close()
        await orch.start()
        for i in range(3):
            await orch.enqueue(f"CHG-DRAIN-{i}")
        await orch.stop(timeout=5.0)
    conn = get_connection(tmp_db)
    try:
        for i in range(3):
            charge = get_charge(conn, f"CHG-DRAIN-{i}")
            assert charge["status"] == "SUCCESS", f"CHG-DRAIN-{i} not SUCCESS: {charge['status']}"
    finally:
        conn.close()  # Windows cannot unlink an open SQLite file

@pytest.mark.asyncio
async def test_stop_is_idempotent(tmp_db):
    orch = RetryOrchestrator(tmp_db)
    await orch.start()
    await orch.stop()
    await orch.stop()  # must not raise