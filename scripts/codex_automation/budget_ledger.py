"""Atomic local budget ledger. No API calls, no credentials, no implicit approval.

This is an optional trusted-runner primitive, NOT a source of provider usage.
The caller must reconcile against independently verified live provider spend.
"""
import json
import os
from decimal import Decimal
from pathlib import Path

CAP = Decimal("8.00")
RESERVE = Decimal("2.00")


def reserve(ledger_path: str, *, month: str, provider_spend: str, task: int) -> str:
    """Return reservation ID, or fail closed. Caller must provide durable shared path.

    Atomic O_EXCL prevents replacing a reservation; one active slot per month.
    This alone is NOT distributed locking across ephemeral GitHub runners.
    """
    if not month or task < 1:
        raise ValueError("invalid task/month")
    spent = Decimal(provider_spend)
    if not spent.is_finite() or spent < 0 or spent + RESERVE > CAP:
        raise ValueError("budget exhausted or invalid")
    directory = Path(ledger_path)
    directory.mkdir(parents=True, exist_ok=True)
    slot = directory / f"{month}.json"
    payload = {"month": month, "task": task, "provider_spend": str(spent),
               "reservation": str(RESERVE), "state": "reserved"}
    fd = os.open(slot, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        slot.unlink(missing_ok=True)
        raise
    return str(slot)


def reconcile(ledger_path: str, *, month: str, task: int, verified_spend: str) -> None:
    slot = Path(ledger_path) / f"{month}.json"
    payload = json.loads(slot.read_text())
    if payload["task"] != task or payload["month"] != month:
        raise ValueError("reservation mismatch")
    amount = Decimal(verified_spend)
    if not amount.is_finite() or amount < 0:
        raise ValueError("invalid provider spend")
    payload.update({"state": "reconciled", "verified_spend": str(amount)})
    slot.write_text(json.dumps(payload))
