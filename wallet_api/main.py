"""Mock Wallet API — FastAPI. Mirrors a real wallet (contacts, billers, transfers,
bill payments, history) with strict idempotency. No real money involved."""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from .db import WalletDB

app = FastAPI(title="Mock Wallet API", version="1.0.0")
db = WalletDB()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TransferRequest(BaseModel):
    contact_id: str
    amount_iqd: int = Field(gt=0)


class BillPaymentRequest(BaseModel):
    biller_id: str
    amount_iqd: int = Field(gt=0)
    account_number: str | None = None


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/users/{user_id}")
def get_user(user_id: str):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(404, "unknown_user")
    return dict(user)


@app.get("/users/{user_id}/contacts")
def search_contacts(user_id: str, q: str = Query(min_length=1)):
    return db.search_contacts(user_id, q)


@app.get("/users/{user_id}/billers")
def search_billers(user_id: str, q: str | None = None):
    if q:
        return db.search_billers(user_id, q)
    return db.list_billers(user_id)


@app.get("/users/{user_id}/transactions")
def get_transactions(user_id: str, limit: int = 10):
    return db.get_transactions(user_id, limit)


@app.post("/users/{user_id}/transfers")
def transfer(
    user_id: str,
    req: TransferRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    """Execute a transfer. Idempotency-Key is mandatory: the same key never pays twice —
    a retry returns the original result instead of executing again."""
    if not db.get_user(user_id):
        raise HTTPException(404, "unknown_user")
    if not db.get_contact(req.contact_id):
        raise HTTPException(404, "unknown_contact")
    try:
        result = db.execute_transfer(
            user_id,
            req.contact_id,
            req.amount_iqd,
            key=idempotency_key,
            txn_id=f"txn_{uuid.uuid4().hex[:12]}",
            created_at=now_iso(),
        )
    except ValueError as e:
        msg = str(e)
        if msg == "unknown_contact":
            raise HTTPException(404, "unknown_contact")
        if msg == "invalid_amount":
            raise HTTPException(422, "invalid_amount")
        raise HTTPException(500, msg)
    return result


@app.post("/users/{user_id}/bill-payments")
def pay_bill(
    user_id: str,
    req: BillPaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    """Execute a bill payment. Same idempotency guarantees as transfers."""
    if not db.get_user(user_id):
        raise HTTPException(404, "unknown_user")
    if not db.get_biller(req.biller_id):
        raise HTTPException(404, "unknown_biller")
    try:
        result = db.execute_bill_payment(
            user_id,
            req.biller_id,
            req.amount_iqd,
            key=idempotency_key,
            txn_id=f"txn_{uuid.uuid4().hex[:12]}",
            created_at=now_iso(),
            account_number=req.account_number,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "unknown_biller":
            raise HTTPException(404, "unknown_biller")
        if msg == "biller_not_linked":
            raise HTTPException(404, "biller_not_linked")
        if msg == "invalid_amount":
            raise HTTPException(422, "invalid_amount")
        raise HTTPException(500, msg)
    return result


@app.post("/admin/reset")
def reset():
    """Reload seed data (useful for demos and tests)."""
    db.load_seed()
    return {"ok": True}
