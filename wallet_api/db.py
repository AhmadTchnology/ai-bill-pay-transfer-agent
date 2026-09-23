"""Mock wallet database (SQLite). No real payment systems involved."""

import json
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "wallet.db"
SEED_PATH = Path(__file__).parent.parent / "data" / "seed_data.json"


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text for fuzzy matching (alef/yaa/taa variants, tashkeel)."""
    if not text:
        return ""
    text = text.strip()
    for ch in ("َ", "ُ", "ِ", "ّ", "ْ", "ٰ"):
        text = text.replace(ch, "")
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ئ", "ي")
    text = text.replace("ة", "ه").replace("ـ", "")
    return text.lower()


# honorifics/titles users say but contacts don't store ("دكتورة ليلى" vs "د. ليلى")
_TITLES = (
    "الدكتوره",
    "الدكتور",
    "الدكتور",
    "دكتوره",
    "دكتور",
    "الد.",
    "الدكتوره",
    "د.",
    "د. ",
    "الاستاذه",
    "الاستاذ",
    "استاذه",
    "استاذ",
    "المهندس",
    "مهندس",
    "الحاج",
    "حاج",
    "الشيخ",
    "شيخ",
    "السيد",
    "سيد",
    "السيدة",
    "سيدة",
)


def strip_titles(text: str) -> str:
    t = normalize_arabic(text)
    for title in _TITLES:
        if t.startswith(title):
            t = t[len(title) :].lstrip(" .·")
            break
    return t


def score_match(query: str, name: str) -> float:
    """Return 0..1 similarity between query and a contact/biller name."""
    import difflib

    q = normalize_arabic(query)
    n = normalize_arabic(name)
    if not q or not n:
        return 0.0
    if q == n:
        return 1.0
    # retry with titles stripped ("الدكتورة ليلى" vs "د. ليلى" -> "ليلى" == "ليلى")
    qs, ns = strip_titles(query), strip_titles(name)
    if qs and ns and qs == ns:
        return 1.0
    ratio = difflib.SequenceMatcher(None, q, n).ratio()
    if qs and ns:
        ratio = max(ratio, difflib.SequenceMatcher(None, qs, ns).ratio())
        if ns.startswith(qs) and qs:
            ratio = max(ratio, 0.9)
    # bonus when name starts with query (e.g. "احمد" -> "احمد علي")
    if n.startswith(q) and q:
        ratio = max(ratio, 0.9)
    return ratio


class WalletDB:
    def __init__(self, db_path: str | Path = DB_PATH, seed: bool = True):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        if seed and not self._has_users():
            self.load_seed()

    def _create_tables(self):
        cur = self.conn
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                balance_iqd INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                bank TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS billers (
                id TEXT PRIMARY KEY,
                name_ar TEXT NOT NULL,
                name_en TEXT NOT NULL,
                category TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_billers (
                user_id TEXT NOT NULL,
                biller_id TEXT NOT NULL,
                account_number TEXT NOT NULL,
                last_amount_iqd INTEGER,
                PRIMARY KEY (user_id, biller_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (biller_id) REFERENCES billers(id)
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,            -- transfer | bill_payment
                counterparty TEXT NOT NULL,
                amount_iqd INTEGER NOT NULL,
                status TEXT NOT NULL,          -- completed | failed
                note TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                key TEXT NOT NULL,
                user_id TEXT NOT NULL,
                transaction_id TEXT,
                response TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (key, user_id)
            );
            """
        )
        cur.commit()

    def _has_users(self):
        return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0

    def load_seed(self, seed_path: str | Path = SEED_PATH):
        data = json.loads(Path(seed_path).read_text(encoding="utf-8"))
        c = self.conn
        c.execute("DELETE FROM users")
        c.execute("DELETE FROM contacts")
        c.execute("DELETE FROM billers")
        c.execute("DELETE FROM user_billers")
        c.execute("DELETE FROM transactions")
        c.execute("DELETE FROM idempotency_keys")
        for u in data["users"]:
            c.execute(
                "INSERT INTO users VALUES (?,?,?,?)",
                (u["id"], u["name"], u["phone"], u["balance_iqd"]),
            )
        for ct in data["contacts"]:
            c.execute(
                "INSERT INTO contacts VALUES (?,?,?,?,?)",
                (ct["id"], ct["user_id"], ct["name"], ct["phone"], ct.get("bank")),
            )
        for b in data["billers"]:
            c.execute(
                "INSERT INTO billers VALUES (?,?,?,?)",
                (b["id"], b["name_ar"], b["name_en"], b["category"]),
            )
        for ub in data["user_billers"]:
            c.execute(
                "INSERT INTO user_billers VALUES (?,?,?,?)",
                (
                    ub["user_id"],
                    ub["biller_id"],
                    ub["account_number"],
                    ub.get("last_amount_iqd"),
                ),
            )
        for t in data.get("transactions", []):
            c.execute(
                "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",
                (
                    t["id"],
                    t["user_id"],
                    t["type"],
                    t["counterparty"],
                    t["amount_iqd"],
                    t["status"],
                    t.get("note"),
                    t["created_at"],
                ),
            )
        c.commit()

    # ---------- reads ----------
    def get_user(self, user_id: str):
        return self.conn.execute(
            "SELECT * FROM users WHERE id=?", (user_id,)
        ).fetchone()

    def search_contacts(self, user_id: str, query: str, threshold: float = 0.62):
        rows = self.conn.execute(
            "SELECT * FROM contacts WHERE user_id=?", (user_id,)
        ).fetchall()
        scored = [(score_match(query, r["name"]), r) for r in rows]
        scored = [(s, r) for s, r in scored if s >= threshold]
        scored.sort(key=lambda x: -x[0])
        return [dict(r) for _, r in scored]

    def get_contact(self, contact_id: str):
        return self.conn.execute(
            "SELECT * FROM contacts WHERE id=?", (contact_id,)
        ).fetchone()

    def search_billers(self, user_id: str, query: str, threshold: float = 0.55):
        rows = self.conn.execute(
            """SELECT b.*, ub.account_number, ub.last_amount_iqd
               FROM billers b JOIN user_billers ub ON b.id = ub.biller_id
               WHERE ub.user_id=?""",
            (user_id,),
        ).fetchall()
        scored = [
            (
                max(
                    score_match(query, r["name_ar"]),
                    score_match(query, r["name_en"]),
                    score_match(query, r["category"]),
                ),
                r,
            )
            for r in rows
        ]
        scored = [(s, r) for s, r in scored if s >= threshold]
        scored.sort(key=lambda x: -x[0])
        return [dict(r) for _, r in scored]

    def list_billers(self, user_id: str):
        rows = self.conn.execute(
            """SELECT b.*, ub.account_number, ub.last_amount_iqd
               FROM billers b JOIN user_billers ub ON b.id = ub.biller_id
               WHERE ub.user_id=? ORDER BY b.name_ar""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_biller(self, biller_id: str):
        return self.conn.execute(
            "SELECT * FROM billers WHERE id=?", (biller_id,)
        ).fetchone()

    def get_transactions(self, user_id: str, limit: int = 10):
        rows = self.conn.execute(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---------- idempotency ----------
    def get_idempotent_response(self, key: str, user_id: str):
        row = self.conn.execute(
            "SELECT * FROM idempotency_keys WHERE key=? AND user_id=?", (key, user_id)
        ).fetchone()
        if row and row["response"]:
            return json.loads(row["response"])
        return None

    # ---------- money movement (atomic + idempotent) ----------
    def execute_transfer(
        self,
        user_id: str,
        contact_id: str,
        amount: int,
        key: str,
        txn_id: str,
        created_at: str,
        note: str | None = None,
    ):
        """Atomically debit user and record transfer. Raises on duplicate key, unknown contact, or
        insufficient balance. Returns a JSON-serializable result dict."""
        with self._lock:
            if self.get_idempotent_response(key, user_id) is not None:
                resp = self.get_idempotent_response(key, user_id)
                resp["duplicate"] = True
                return resp
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                user = self.conn.execute(
                    "SELECT balance_iqd FROM users WHERE id=?", (user_id,)
                ).fetchone()
                if user is None:
                    raise ValueError("unknown_user")
                contact = self.conn.execute(
                    "SELECT * FROM contacts WHERE id=? AND user_id=?",
                    (contact_id, user_id),
                ).fetchone()
                if contact is None:
                    raise ValueError("unknown_contact")
                if amount <= 0:
                    raise ValueError("invalid_amount")
                if user["balance_iqd"] < amount:
                    self.conn.execute("ROLLBACK")
                    resp = {
                        "ok": False,
                        "error": "insufficient_funds",
                        "message": f"الرصيد غير كافٍ. رصيدك الحالي {user['balance_iqd']:,} د.ع والمبلغ المطلوب {amount:,} د.ع",
                        "transaction_id": None,
                    }
                    self.conn.execute(
                        "INSERT OR REPLACE INTO idempotency_keys VALUES (?,?,?,?,?)",
                        (
                            key,
                            user_id,
                            None,
                            json.dumps(resp, ensure_ascii=False),
                            created_at,
                        ),
                    )
                    self.conn.commit()
                    return resp
                new_balance = user["balance_iqd"] - amount
                self.conn.execute(
                    "UPDATE users SET balance_iqd=? WHERE id=?", (new_balance, user_id)
                )
                self.conn.execute(
                    "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",
                    (
                        txn_id,
                        user_id,
                        "transfer",
                        contact["name"],
                        amount,
                        "completed",
                        note,
                        created_at,
                    ),
                )
                resp = {
                    "ok": True,
                    "transaction_id": txn_id,
                    "amount_iqd": amount,
                    "recipient": contact["name"],
                    "new_balance_iqd": new_balance,
                    "duplicate": False,
                }
                self.conn.execute(
                    "INSERT OR REPLACE INTO idempotency_keys VALUES (?,?,?,?,?)",
                    (
                        key,
                        user_id,
                        txn_id,
                        json.dumps(resp, ensure_ascii=False),
                        created_at,
                    ),
                )
                self.conn.commit()
                return resp
            except ValueError:
                self.conn.execute("ROLLBACK")
                raise

    def execute_bill_payment(
        self,
        user_id: str,
        biller_id: str,
        amount: int,
        key: str,
        txn_id: str,
        created_at: str,
        account_number: str | None = None,
    ):
        """Atomically pay a bill. Same idempotency rules as transfers."""
        with self._lock:
            if self.get_idempotent_response(key, user_id) is not None:
                resp = self.get_idempotent_response(key, user_id)
                resp["duplicate"] = True
                return resp
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                user = self.conn.execute(
                    "SELECT balance_iqd FROM users WHERE id=?", (user_id,)
                ).fetchone()
                if user is None:
                    raise ValueError("unknown_user")
                biller = self.conn.execute(
                    "SELECT * FROM billers WHERE id=?", (biller_id,)
                ).fetchone()
                if biller is None:
                    raise ValueError("unknown_biller")
                ub = self.conn.execute(
                    "SELECT * FROM user_billers WHERE user_id=? AND biller_id=?",
                    (user_id, biller_id),
                ).fetchone()
                if ub is None:
                    raise ValueError("biller_not_linked")
                if amount <= 0:
                    raise ValueError("invalid_amount")
                acct = account_number or ub["account_number"]
                if user["balance_iqd"] < amount:
                    self.conn.execute("ROLLBACK")
                    resp = {
                        "ok": False,
                        "error": "insufficient_funds",
                        "message": f"الرصيد غير كافٍ. رصيدك الحالي {user['balance_iqd']:,} د.ع والمبلغ المطلوب {amount:,} د.ع",
                        "transaction_id": None,
                    }
                    self.conn.execute(
                        "INSERT OR REPLACE INTO idempotency_keys VALUES (?,?,?,?,?)",
                        (
                            key,
                            user_id,
                            None,
                            json.dumps(resp, ensure_ascii=False),
                            created_at,
                        ),
                    )
                    self.conn.commit()
                    return resp
                new_balance = user["balance_iqd"] - amount
                self.conn.execute(
                    "UPDATE users SET balance_iqd=? WHERE id=?", (new_balance, user_id)
                )
                self.conn.execute(
                    "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)",
                    (
                        txn_id,
                        user_id,
                        "bill_payment",
                        biller["name_ar"],
                        amount,
                        "completed",
                        f"حساب رقم {acct}",
                        created_at,
                    ),
                )
                self.conn.execute(
                    "UPDATE user_billers SET last_amount_iqd=? WHERE user_id=? AND biller_id=?",
                    (amount, user_id, biller_id),
                )
                resp = {
                    "ok": True,
                    "transaction_id": txn_id,
                    "amount_iqd": amount,
                    "biller": biller["name_ar"],
                    "account_number": acct,
                    "new_balance_iqd": new_balance,
                    "duplicate": False,
                }
                self.conn.execute(
                    "INSERT OR REPLACE INTO idempotency_keys VALUES (?,?,?,?,?)",
                    (
                        key,
                        user_id,
                        txn_id,
                        json.dumps(resp, ensure_ascii=False),
                        created_at,
                    ),
                )
                self.conn.commit()
                return resp
            except ValueError:
                self.conn.execute("ROLLBACK")
                raise
