import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from app.database import (
    get_connection, get_charge, update_charge_status, insert_attempt,
)
from app.synthetic_processor import process_payment, FAILURE_RATE


class RetryOrchestrator:
    def __init__(self, db_path: str, failure_rate: float = FAILURE_RATE):
        self.db_path = db_path
        self.failure_rate = failure_rate
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._process_queue())

    async def stop(self, timeout: float = 10.0) -> None:
        if self._task is None:
            return
        try:
            await asyncio.wait_for(self._queue.join(), timeout)
        except asyncio.TimeoutError:
            pass
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def enqueue(self, charge_id: str, delay_seconds: float = 0) -> None:
        await self._queue.put((charge_id, delay_seconds))

    @staticmethod
    def compute_backoff_delays(max_retries: int) -> list[int]:
        return [2 ** i for i in range(max_retries)]

    def queue_depth(self) -> int:
        return self._queue.qsize()

    async def _process_queue(self) -> None:
        while True:
            charge_id, delay = await self._queue.get()
            try:
                if delay > 0:
                    await asyncio.sleep(delay)
                await self._attempt_charge(charge_id)
            except Exception:
                pass
            finally:
                self._queue.task_done()

    async def _attempt_charge(self, charge_id: str) -> None:
        conn = get_connection(self.db_path)
        try:
            charge = get_charge(conn, charge_id)
            if not charge or charge["status"] in ("SUCCESS", "FAILED"):
                return
            update_charge_status(conn, charge_id, "PROCESSING")
            attempt_number = charge["retry_count"] + 1
            resp = await process_payment(charge_id, charge["amount"], self.failure_rate)
            insert_attempt(
                conn, charge_id, attempt_number,
                "SUCCESS" if resp.success else "FAILED",
                resp.error_code, resp.error_message,
                json.dumps(asdict(resp)), resp.duration_ms,
            )
            if resp.success:
                update_charge_status(conn, charge_id, "SUCCESS")
                return
            if attempt_number > charge["max_retries"]:
                update_charge_status(conn, charge_id, "FAILED")
                return
            delays = self.compute_backoff_delays(charge["max_retries"])
            delay = delays[attempt_number - 1] if attempt_number - 1 < len(delays) else delays[-1]
            next_retry = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
            update_charge_status(conn, charge_id, "PENDING",
                                 retry_count=attempt_number, next_retry_at=next_retry)
            await self.enqueue(charge_id, delay_seconds=delay)
        finally:
            conn.close()
