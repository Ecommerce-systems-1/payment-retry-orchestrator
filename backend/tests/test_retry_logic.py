import os
import tempfile
import pytest
from unittest.mock import patch
from app.database import init_db, get_connection, insert_charge, get_charge, get_attempts
from app.retry_orchestrator import RetryOrchestrator
from app.synthetic_processor import ProcessorResponse


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def test_backoff_delays_are_exponential():
    assert RetryOrchestrator.compute_backoff_delays(3) == [1, 2, 4]
    assert RetryOrchestrator.compute_backoff_delays(0) == []


def test_queue_depth_starts_empty(tmp_db):
    orch = RetryOrchestrator(tmp_db)
    assert orch.queue_depth() == 0


@pytest.mark.asyncio
async def test_exhausted_retries_mark_charge_failed(tmp_db):
    fail_resp = ProcessorResponse(False, None, "card_declined", "Declined", 10)
    with patch("app.retry_orchestrator.process_payment", return_value=fail_resp), \
         patch.object(RetryOrchestrator, "compute_backoff_delays",
                      staticmethod(lambda n: [0] * n)):
        orch = RetryOrchestrator(tmp_db)
        conn = get_connection(tmp_db)
        insert_charge(conn, "CHG-FAIL", 10.0, "USD", "c1", None, 2)
        conn.close()
        await orch.start()
        await orch.enqueue("CHG-FAIL")
        await orch.stop(timeout=5.0)
    conn = get_connection(tmp_db)
    charge = get_charge(conn, "CHG-FAIL")
    attempts = get_attempts(conn, "CHG-FAIL")
    conn.close()
    assert charge["status"] == "FAILED"
    assert len(attempts) == 3  # initial attempt + 2 retries
    assert all(a["status"] == "FAILED" for a in attempts)
