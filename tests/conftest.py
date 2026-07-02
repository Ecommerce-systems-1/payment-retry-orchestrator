import pytest
import asyncio
import tempfile, os
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from backend.synthetic_processor import ProcessorResponse

SUCCESS_RESP = ProcessorResponse(True, "txn_test_1234", None, None, 100)
FAIL_RESP    = ProcessorResponse(False, None, "CARD_DECLINED", "Payment declined: CARD_DECLINED", 100)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def app_with_success_processor():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    with patch.dict(os.environ, {"DB_PATH": db_path}):
        with patch("backend.retry_orchestrator.process_payment", return_value=SUCCESS_RESP):
            from backend.main import create_app
            application = create_app(db_path=db_path)
            async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as ac:
                yield ac
    os.unlink(db_path)

@pytest.fixture
async def client(app_with_success_processor):
    return app_with_success_processor

# tests/test_charges.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_post_charge_returns_201(client: AsyncClient):
    r = await client.post("/charge", json={
        "charge_id": "CHG-T1", "amount": 99.99, "currency": "USD", "customer_id": "CUST-1"
    })
    assert r.status_code == 201
    body = r.json()
    assert body["charge_id"] == "CHG-T1"
    assert body["status"] == "PENDING"

@pytest.mark.asyncio
async def test_get_charge_status(client: AsyncClient):
    await client.post("/charge", json={
        "charge_id": "CHG-T2", "amount": 20.0, "currency": "USD", "customer_id": "CUST-2"
    })
    r = await client.get("/charge/CHG-T2/status")
    assert r.status_code == 200
    data = r.json()
    assert data["charge_id"] == "CHG-T2"
    assert data["amount"] == 20.0
    assert data["status"] in ["PENDING","PROCESSING","SUCCESS","FAILED"]
    assert isinstance(data["attempts"], list)

@pytest.mark.asyncio
async def test_get_unknown_charge_returns_404(client: AsyncClient):
    r = await client.get("/charge/DOES-NOT-EXIST/status")
    assert r.status_code == 404

@pytest.mark.asyncio
async def test_invalid_amount_returns_422(client: AsyncClient):
    r = await client.post("/charge", json={
        "charge_id": "CHG-BAD", "amount": -5.0, "currency": "USD", "customer_id": "C1"
    })
    assert r.status_code == 422

# tests/test_idempotency.py
@pytest.mark.asyncio
async def test_duplicate_charge_id_returns_200(client: AsyncClient):
    payload = {"charge_id": "CHG-IDEM", "amount": 50.0, "currency": "USD", "customer_id": "C1"}
    r1 = await client.post("/charge", json=payload)
    r2 = await client.post("/charge", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["charge_id"] == r2.json()["charge_id"]

# tests/test_stats.py
@pytest.mark.asyncio
async def test_stats_endpoint_returns_expected_shape(client: AsyncClient):
    r = await client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    for key in ["total_charges","success_count","failed_count","pending_count",
                "processing_count","success_rate","avg_attempts_to_success","queue_depth"]:
        assert key in data