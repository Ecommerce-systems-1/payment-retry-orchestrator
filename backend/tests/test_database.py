import os
import tempfile
import pytest
from app.database import (
    init_db, get_connection, insert_charge, get_charge,
    update_charge_status, insert_attempt, get_attempts, get_stats,
)


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    yield path
    os.unlink(path)


def test_insert_and_get_charge(tmp_db):
    conn = get_connection(tmp_db)
    insert_charge(conn, "CHG-1", 25.0, "USD", "cust-1", "Test charge", 3)
    charge = get_charge(conn, "CHG-1")
    assert charge["id"] == "CHG-1"
    assert charge["amount"] == 25.0
    assert charge["status"] == "PENDING"
    assert charge["retry_count"] == 0
    conn.close()


def test_get_missing_charge_returns_none(tmp_db):
    conn = get_connection(tmp_db)
    assert get_charge(conn, "CHG-NOPE") is None
    conn.close()


def test_update_charge_status(tmp_db):
    conn = get_connection(tmp_db)
    insert_charge(conn, "CHG-2", 10.0, "USD", "cust-1", None, 3)
    update_charge_status(conn, "CHG-2", "SUCCESS", retry_count=1)
    charge = get_charge(conn, "CHG-2")
    assert charge["status"] == "SUCCESS"
    assert charge["retry_count"] == 1
    conn.close()


def test_attempts_recorded_in_order(tmp_db):
    conn = get_connection(tmp_db)
    insert_charge(conn, "CHG-3", 10.0, "USD", "cust-1", None, 3)
    insert_attempt(conn, "CHG-3", 1, "FAILED", "card_declined", "Declined", "{}", 120)
    insert_attempt(conn, "CHG-3", 2, "SUCCESS", None, None, "{}", 80)
    attempts = get_attempts(conn, "CHG-3")
    assert [a["attempt_number"] for a in attempts] == [1, 2]
    assert attempts[1]["status"] == "SUCCESS"
    conn.close()


def test_stats(tmp_db):
    conn = get_connection(tmp_db)
    insert_charge(conn, "CHG-4", 10.0, "USD", "c1", None, 3)
    insert_charge(conn, "CHG-5", 20.0, "USD", "c2", None, 3)
    update_charge_status(conn, "CHG-4", "SUCCESS")
    update_charge_status(conn, "CHG-5", "FAILED")
    insert_attempt(conn, "CHG-4", 2, "SUCCESS", None, None, "{}", 50)
    stats = get_stats(conn)
    assert stats["total_charges"] == 2
    assert stats["success_count"] == 1
    assert stats["failed_count"] == 1
    assert stats["success_rate"] == 0.5
    assert stats["avg_attempts_to_success"] == 2.0
    conn.close()
