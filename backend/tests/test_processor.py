import asyncio
import pytest
from app.synthetic_processor import process_payment, ProcessorResponse


@pytest.mark.asyncio
async def test_zero_failure_rate_always_succeeds():
    resp = await process_payment("CHG-1", 25.0, failure_rate=0.0)
    assert isinstance(resp, ProcessorResponse)
    assert resp.success is True
    assert resp.transaction_id is not None
    assert resp.error_code is None
    assert resp.duration_ms > 0


@pytest.mark.asyncio
async def test_full_failure_rate_always_fails():
    resp = await process_payment("CHG-2", 25.0, failure_rate=1.0)
    assert resp.success is False
    assert resp.transaction_id is None
    assert resp.error_code is not None
    assert resp.error_message
