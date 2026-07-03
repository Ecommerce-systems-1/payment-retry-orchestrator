import asyncio
import random
import uuid
from dataclasses import dataclass

FAILURE_RATE = 0.3

ERROR_CODES = [
    ("card_declined", "Card was declined by the issuing bank"),
    ("insufficient_funds", "Insufficient funds on the card"),
    ("processor_timeout", "Payment processor timed out"),
    ("network_error", "Transient network error"),
]


@dataclass
class ProcessorResponse:
    success: bool
    transaction_id: str | None
    error_code: str | None
    error_message: str | None
    duration_ms: int


async def process_payment(charge_id: str, amount: float,
                          failure_rate: float = FAILURE_RATE) -> ProcessorResponse:
    duration_ms = random.randint(30, 250)
    await asyncio.sleep(duration_ms / 1000)
    if random.random() < failure_rate:
        code, msg = random.choice(ERROR_CODES)
        return ProcessorResponse(False, None, code, msg, duration_ms)
    return ProcessorResponse(True, f"txn_{uuid.uuid4().hex[:12]}", None, None, duration_ms)
