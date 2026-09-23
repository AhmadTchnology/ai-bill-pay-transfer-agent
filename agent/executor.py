"""Executor: the ONLY component that talks to the wallet for money movement.

Idempotency design (competition requirement: retries never cause a double
payment):
1. A proposal gets an idempotency key at creation time (hash of session id,
   intent and a per-proposal nonce) — NOT at execution time.
2. The executor retries failed HTTP calls with the SAME key. The wallet stores
   key -> transaction; a retry returns the original result instead of paying
   again, even if the first attempt actually succeeded server-side.
3. A new confirmation (different proposal) always gets a new key, so a
   legitimate second transfer of the same amount to the same person still works.
"""

import hashlib
import os

import httpx

WALLET_URL = os.environ.get("WALLET_URL", "http://127.0.0.1:8001")


class WalletError(Exception):
    def __init__(self, message: str, code: str = "wallet_error"):
        super().__init__(message)
        self.code = code


class WalletClient:
    def __init__(self, base_url: str = WALLET_URL, timeout: float = 10.0):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None):
        r = httpx.get(f"{self.base}{path}", params=params or {}, timeout=self.timeout)
        if r.status_code == 404:
            raise WalletError(
                "not found", code=str(r.json().get("detail", "not_found"))
            )
        r.raise_for_status()
        return r.json()

    def _post(
        self, path: str, payload: dict, idempotency_key: str, max_attempts: int = 3
    ):
        """POST with retries. Network-level failures are retried with the SAME
        idempotency key so the wallet can deduplicate safely."""
        last_exc = None
        for _ in range(max_attempts):
            try:
                r = httpx.post(
                    f"{self.base}{path}",
                    json=payload,
                    headers={"Idempotency-Key": idempotency_key},
                    timeout=self.timeout,
                )
                if r.status_code >= 500:
                    raise httpx.TransportError(f"server error {r.status_code}")
                if r.status_code in (404, 422):
                    return r.json()
                r.raise_for_status()
                return r.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last_exc = e
        raise WalletError(
            f"تعذر الوصول للمحفظة بعد {max_attempts} محاولات: {last_exc}",
            code="wallet_unreachable",
        )

    # ---- reads ----
    def get_user(self, user_id: str) -> dict:
        try:
            return self._get(f"/users/{user_id}")
        except WalletError:
            return {}

    def search_contacts(self, user_id: str, q: str) -> list:
        try:
            return self._get(f"/users/{user_id}/contacts", {"q": q})
        except WalletError:
            return []

    def search_billers(self, user_id: str, q: str | None = None) -> list:
        try:
            params = {"q": q} if q else None
            return self._get(f"/users/{user_id}/billers", params)
        except WalletError:
            return []

    def get_transactions(self, user_id: str, limit: int = 10) -> list:
        try:
            return self._get(f"/users/{user_id}/transactions", {"limit": limit})
        except WalletError:
            return []

    # ---- money movement ----
    def transfer(
        self, user_id: str, contact_id: str, amount: int, idempotency_key: str
    ) -> dict:
        return self._post(
            f"/users/{user_id}/transfers",
            {"contact_id": contact_id, "amount_iqd": amount},
            idempotency_key,
        )

    def pay_bill(
        self, user_id: str, biller_id: str, amount: int, idempotency_key: str
    ) -> dict:
        return self._post(
            f"/users/{user_id}/bill-payments",
            {"biller_id": biller_id, "amount_iqd": amount},
            idempotency_key,
        )


def make_idempotency_key(session_id: str, proposal_nonce: str) -> str:
    """Stable, unique per proposal. Generated BEFORE execution so retries reuse it."""
    return hashlib.sha256(f"{session_id}:{proposal_nonce}".encode()).hexdigest()[:40]
