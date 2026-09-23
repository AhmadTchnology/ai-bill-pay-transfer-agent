"""Session: the conversation state machine.

States:
  IDLE                    - waiting for a new request
  AWAITING_CHOICE         - asked "which Ahmed?", waiting for a pick
  AWAITING_AMOUNT         - know who/what, missing amount
  AWAITING_CONFIRMATION   - proposal shown on a card, waiting for explicit yes

Hard rules enforced here:
- NOTHING reaches the executor unless state == AWAITING_CONFIRMATION and the
  user's reply matches a rule-based confirmation word (regex list, not the LLM).
- Cancel words are checked FIRST ("لا زين" is a cancel, not a confirm).
- Ambiguity always becomes a question to the user, never a guess.
- Multi-intent requests ("pay electricity AND send 5k to Zainab") resolve every
  intent first; one confirmation card lists ALL proposals; one "نعم" executes
  all of them (or nothing, if the user says "لا").
"""

import re
import uuid

from . import nlu
from .executor import WalletClient, make_idempotency_key
from .resolver import resolve_biller, resolve_contact

CANCEL_WORDS = re.compile(r"^\s*(لا|لاء|الغي|الغاء|إلغاء|وقف|خلاص|كنسل|كنسلة)\b")
CONFIRM_WORDS = re.compile(
    r"^\s*(نعم|أيوة|ايوة|ايوا|اكيد|أكيد|اكد|أكد|صح|زين|نفذ|نفذها|سويها|ok|okay|yes|y)\b",
    re.IGNORECASE,
)


def fmt_iqd(n: int) -> str:
    return f"{n:,} د.ع"


class Proposal:
    """A fully-resolved transaction awaiting user confirmation."""

    def __init__(self, session_id: str, kind: str, amount: int, counterparty: dict):
        self.id = uuid.uuid4().hex[:8]
        self.kind = kind  # transfer | bill_pay
        self.amount = amount
        self.counterparty = counterparty
        # Idempotency key is minted at PROPOSAL time, not execution time.
        # Retries reuse it; the wallet deduplicates on it.
        self.idempotency_key = make_idempotency_key(session_id, self.id)

    def describe(self) -> dict:
        if self.kind == "transfer":
            c = self.counterparty
            return {
                "type": "تحويل",
                "to": c["name"],
                "detail": f"رقم: {c['phone']} • {c.get('bank') or ''}".strip(" •"),
                "amount": self.amount,
            }
        b = self.counterparty
        return {
            "type": "دفع فاتورة",
            "to": b["name_ar"],
            "detail": f"حساب رقم: {b.get('account_number') or '—'}",
            "amount": self.amount,
        }


class Reply:
    def __init__(self):
        self.messages = []  # text messages to show
        self.cards = []  # confirmation cards
        self.choices = None  # disambiguation option labels
        self.executed = []  # results of executed transactions


class Session:
    def __init__(
        self, user_id: str, wallet: WalletClient, session_id: str | None = None
    ):
        self.user_id = user_id
        self.wallet = wallet
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.state = "IDLE"
        self.proposals: list[Proposal] = []
        self.pending_intents: list[dict] = []
        self.pending_amount: int | None = None  # amount stated before the recipient
        self.current_intent: dict | None = None
        self.options: list[dict] = []
        self.history: list[dict] = []

    # ------------------------------------------------------------------ #
    def handle(self, text: str) -> Reply:
        self.history.append({"role": "user", "content": text})
        reply = Reply()
        try:
            if self.state == "AWAITING_CONFIRMATION":
                return self._handle_confirmation_reply(text)
            if self.state == "AWAITING_CHOICE":
                return self._handle_choice(text)
            if self.state == "AWAITING_AMOUNT":
                return self._handle_amount(text)
            return self._handle_new_request(text, reply)
        except RuntimeError as e:
            reply.messages.append(f"صار خطأ بفهم الطلب: {e}. جرب مرة ثانية.")
            self.state = "IDLE"
            return reply

    # ------------------------------------------------------------------ #
    def _update_pending_amount(self, intents: list[dict]):
        """Track an amount stated before/without its counterparty ("حول 20000").
        It survives across turns until used, superseded by a fresh amount, or the
        user clearly moved on (query/smalltalk). Deterministic carry-over beats
        relying on the LLM's conversational memory."""
        has_amount = any(i.get("amount") for i in intents)
        actions = {i.get("action") for i in intents}
        if has_amount:
            if (
                len(intents) == 1
                and intents[0].get("amount")
                and not intents[0].get("recipient")
                and not intents[0].get("biller")
            ):
                self.pending_amount = intents[0]["amount"]  # remember "حول 20000"
            else:
                self.pending_amount = None  # fresh amounts are consumed directly
        else:
            if not (actions & {"transfer", "bill_pay"}):
                self.pending_amount = None  # user moved on

    def _handle_new_request(self, text: str, reply: Reply) -> Reply:
        nlu_result = nlu.extract_intents(text, self.history)
        intents = [i for i in nlu_result.get("intents", []) if isinstance(i, dict)]
        if not intents:
            intents = [{"action": "unknown"}]
        self.pending_intents = list(intents)
        self._update_pending_amount(intents)
        return self._process_next_intent(reply)

    def _process_next_intent(self, reply: Reply) -> Reply:
        while self.pending_intents:
            intent = self.pending_intents.pop(0)
            self.current_intent = intent
            action = intent.get("action", "unknown")
            if action == "transfer":
                step = self._step_transfer(intent, reply)
            elif action == "bill_pay":
                step = self._step_bill_pay(intent, reply)
            elif action == "balance_check":
                user = self.wallet.get_user(self.user_id)
                reply.messages.append(
                    f"رصيدك الحالي {fmt_iqd(user.get('balance_iqd', 0))}."
                )
                continue
            elif action == "history":
                txns = self.wallet.get_transactions(self.user_id, 5)
                if not txns:
                    reply.messages.append("ما عندك حركات سابقة.")
                    continue
                lines = ["آخر الحركات:"]
                for t in txns:
                    kind = "تحويل" if t["type"] == "transfer" else "فاتورة"
                    lines.append(
                        f"• {t['created_at'][:10]} — {t['counterparty']}: {fmt_iqd(t['amount_iqd'])} ({kind})"
                    )
                reply.messages.append("\n".join(lines))
                continue
            else:
                reply.messages.append(
                    "ما فهمت الطلب. گلي مثلاً: «دفع فاتورة الكهرباء» أو «حول 50 الف لأحمد»."
                )
                self.state = "IDLE"
                return reply
            if step == "PAUSED":
                return (
                    reply  # waiting on the user (amount / choice / nothing more to do)
                )
            # step == "PROPOSED" -> keep resolving remaining intents
        return self._finalize(reply)

    def _finalize(self, reply: Reply) -> Reply:
        """Called when no intents remain pending: show one card for all proposals."""
        if not self.proposals:
            self.state = "IDLE"
            return reply
        self.state = "AWAITING_CONFIRMATION"
        user = self.wallet.get_user(self.user_id)
        balance = user.get("balance_iqd", 0)
        after = balance - sum(p.amount for p in self.proposals)
        reply.cards.append(
            {
                "proposals": [p.describe() for p in self.proposals],
                "balance_before": balance,
                "balance_after": after,
            }
        )
        reply.messages.append("تك تنفيذ؟ جاوب «نعم» للتنفيذ أو «لا» للإلغاء.")
        return reply

    # ------------------------------------------------------------------ #
    def _step_transfer(self, intent: dict, reply: Reply) -> str:
        name = intent.get("recipient")
        amount = intent.get("amount")
        if amount and self.pending_amount and amount != self.pending_amount:
            self.pending_amount = None  # fresh amount stated — drop the stale one
        if not amount and self.pending_amount:
            amount = self.pending_amount
            self.pending_amount = None
        if not name:
            reply.messages.append("لمين تريد تحول؟ اكتب الاسم.")
            self.state = "IDLE"
            return "PAUSED"
        matches = self.wallet.search_contacts(self.user_id, name)
        res = resolve_contact(matches, name)
        if res["status"] == "not_found":
            reply.messages.append(
                f"ما ألقى اسم «{name}» بجهاتك. تأكد من الاسم، أو گلي الرقم الصح."
            )
            self.state = "IDLE"
            return "PAUSED"
        if res["status"] == "ambiguous":
            self.options = res["options"]
            self.state = "AWAITING_CHOICE"
            labels = [
                f"{i + 1}. {c['name']} — {c['phone']} ({c.get('bank') or 'محفظة'})"
                for i, c in enumerate(self.options)
            ]
            reply.messages.append(
                "عندك أكثر من واحد بنفس الاسم. تقصد:\n" + "\n".join(labels)
            )
            reply.choices = [c["name"] for c in self.options]
            return "PAUSED"
        contact = res["contact"]
        if not amount:
            reply.messages.append(
                f"شلون تريد تحول إلى {contact['name']}؟ (المبلغ بالدينار)"
            )
            self.state = "AWAITING_AMOUNT"
            return "PAUSED"
        return self._propose_transfer(contact, int(amount), reply)

    def _step_bill_pay(self, intent: dict, reply: Reply) -> str:
        biller_name = intent.get("biller")
        amount = intent.get("amount")
        if not amount and self.pending_amount:
            amount = self.pending_amount
            self.pending_amount = None
        if not biller_name:
            reply.messages.append(
                "أي فاتورة تريد تدفع؟ (كهرباء، ماء، انترنت، موبايل...)"
            )
            self.state = "IDLE"
            return "PAUSED"
        billers = self.wallet.search_billers(self.user_id, biller_name)
        res = resolve_biller(billers, biller_name)
        if res["status"] == "not_found":
            all_billers = self.wallet.search_billers(self.user_id)
            names = (
                "\n".join(f"• {b['name_ar']}" for b in all_billers)
                or "• ما عندك فواتير مسجلة"
            )
            reply.messages.append(
                f"ما ألقى شركة فواتير بهذا الاسم. الفواتير المسجلة عندك:\n{names}"
            )
            self.state = "IDLE"
            return "PAUSED"
        if res["status"] == "ambiguous":
            self.options = res["options"]
            self.state = "AWAITING_CHOICE"
            labels = [f"{i + 1}. {b['name_ar']}" for i, b in enumerate(self.options)]
            reply.messages.append("تقصد أي وحدة؟\n" + "\n".join(labels))
            reply.choices = [b["name_ar"] for b in self.options]
            return "PAUSED"
        biller = res["biller"]
        if not amount:
            suggestion = biller.get("last_amount_iqd")
            hint = f" (آخر مرة دفعت {fmt_iqd(suggestion)})" if suggestion else ""
            reply.messages.append(f"شلون تريد تدفع لـ{biller['name_ar']}؟{hint}")
            self.state = "AWAITING_AMOUNT"
            return "PAUSED"
        return self._propose_bill(biller, int(amount), reply)

    # ------------------------------------------------------------------ #
    def _available_balance(self) -> int:
        user = self.wallet.get_user(self.user_id)
        return user.get("balance_iqd", 0) - sum(p.amount for p in self.proposals)

    def _reject_insufficient(self, available: int, amount: int, reply: Reply) -> str:
        """Honest early rejection. If this was part of a multi-intent request, the
        ENTIRE request is dropped — we never execute half of what was asked."""
        dropped = bool(self.proposals) or bool(self.pending_intents)
        self.proposals = []
        self.pending_intents = []
        self.state = "IDLE"
        msg = (
            f"الرصيد ما يكفي: متوفر عندك {fmt_iqd(available)} والمطلوب {fmt_iqd(amount)}. "
            f"خلّي المبلغ أقل أو اشحن المحفظة أول."
        )
        if dropped:
            msg += " (عطلنا الطلب كله حتى ما ينحولّ شي نص طلب)"
        reply.messages.append(msg)
        return "PAUSED"

    def _propose_transfer(self, contact: dict, amount: int, reply: Reply) -> str:
        if amount <= 0:
            reply.messages.append("المبلغ لازم يكون أكبر من صفر.")
            self.state = "IDLE"
            return "PAUSED"
        available = self._available_balance()
        if amount > available:
            return self._reject_insufficient(available, amount, reply)
        self.proposals.append(Proposal(self.session_id, "transfer", amount, contact))
        if self.pending_intents:
            return self._process_next_intent(reply)  # resolve remaining intents first
        return self._finalize(reply)

    def _propose_bill(self, biller: dict, amount: int, reply: Reply) -> str:
        if amount <= 0:
            reply.messages.append("المبلغ لازم يكون أكبر من صفر.")
            self.state = "IDLE"
            return "PAUSED"
        available = self._available_balance()
        if amount > available:
            return self._reject_insufficient(available, amount, reply)
        available = self._available_balance()
        if amount > available:
            reply.messages.append(
                f"الرصيد ما يكفي: متوفر عندك {fmt_iqd(available)} والمطلوب {fmt_iqd(amount)}. "
                f"خلّي المبلغ أقل أو اشحن المحفظة أول."
            )
            self.state = "IDLE"
            return "PAUSED"
        self.proposals.append(Proposal(self.session_id, "transfer", amount, contact))
        if self.pending_intents:
            return self._process_next_intent(reply)  # resolve remaining intents first
        return self._finalize(reply)

    def _propose_bill(self, biller: dict, amount: int, reply: Reply) -> str:
        if amount <= 0:
            reply.messages.append("المبلغ لازم يكون أكبر من صفر.")
            self.state = "IDLE"
            return "PAUSED"
        available = self._available_balance()
        if amount > available:
            reply.messages.append(
                f"الرصيد ما يكفي: متوفر عندك {fmt_iqd(available)} والمطلوب {fmt_iqd(amount)}. "
                f"خلّي المبلغ أقل أو اشحن المحفظة أول."
            )
            self.state = "IDLE"
            return "PAUSED"
        self.proposals.append(Proposal(self.session_id, "bill_pay", amount, biller))
        if self.pending_intents:
            return self._process_next_intent(reply)
        return self._finalize(reply)

    # ------------------------------------------------------------------ #
    def _handle_confirmation_reply(self, text: str) -> Reply:
        reply = Reply()
        clean = text.strip()
        if CANCEL_WORDS.search(clean):
            self.proposals = []
            self.state = "IDLE"
            reply.messages.append("تم الإلغاء. ما انحولّ شي.")
            return reply
        if CONFIRM_WORDS.search(clean):
            return self._execute_proposals(reply)
        self.proposals = []
        self.state = "IDLE"
        reply.messages.append("ما اكتبت تأكيد واضح — عطلنا الطلب. ما انحولّ شي.")
        return reply

    def _execute_proposals(self, reply: Reply) -> Reply:
        for p in self.proposals:
            desc = p.describe()
            try:
                if p.kind == "transfer":
                    result = self.wallet.transfer(
                        self.user_id, p.counterparty["id"], p.amount, p.idempotency_key
                    )
                else:
                    result = self.wallet.pay_bill(
                        self.user_id, p.counterparty["id"], p.amount, p.idempotency_key
                    )
            except Exception as e:
                reply.messages.append(
                    f"فشل تنفيذ العملية ({desc['to']} — {fmt_iqd(p.amount)}): {e}. "
                    f"ما انحولّ شي بهذه العملية."
                )
                reply.executed.append(
                    {"ok": False, "to": desc["to"], "amount": p.amount}
                )
                continue
            if result.get("ok"):
                who = result.get("recipient") or result.get("biller")
                note = (
                    " (ملاحظة: هذي نتيجة العملية السابقة — ما اندفع مرتين)"
                    if result.get("duplicate")
                    else ""
                )
                reply.messages.append(
                    f"تم بنجاح: {fmt_iqd(result['amount_iqd'])} إلى {who}. "
                    f"رقم العملية: {result['transaction_id']}. رصيدك الجديد: {fmt_iqd(result['new_balance_iqd'])}.{note}"
                )
                reply.executed.append(
                    {
                        "ok": True,
                        "to": who,
                        "amount": result["amount_iqd"],
                        "txn": result["transaction_id"],
                    }
                )
            else:
                reply.messages.append(
                    f"ما اننفذت العملية: {result.get('message', 'سبب غير معروف')}"
                )
                reply.executed.append(
                    {"ok": False, "to": desc["to"], "amount": p.amount}
                )
        self.proposals = []
        self.state = "IDLE"
        return reply

    # ------------------------------------------------------------------ #
    def _handle_choice(self, text: str) -> Reply:
        reply = Reply()
        clean = text.strip()
        if CANCEL_WORDS.search(clean):
            self.options = []
            self.pending_intents = []
            self.proposals = []
            self.state = "IDLE"
            reply.messages.append("تم الإلغاء. ما انحولّ شي.")
            return reply
        pick = None
        m = re.match(r"^(\d+)$", clean)
        if m and 1 <= int(m.group(1)) <= len(self.options):
            pick = self.options[int(m.group(1)) - 1]
        else:
            from wallet_api.db import score_match

            best, best_s = None, 0.0
            for opt in self.options:
                s = score_match(clean, opt.get("name") or opt.get("name_ar", ""))
                if s > best_s:
                    best, best_s = opt, s
            if best and best_s >= 0.5:
                pick = best
        if pick is None:
            labels = [
                f"{i + 1}. {c.get('name') or c.get('name_ar')}"
                for i, c in enumerate(self.options)
            ]
            reply.messages.append(
                "اختر رقم أو اكتب الاسم الكامل:\n" + "\n".join(labels)
            )
            return reply
        intent = self.current_intent or {}
        amount = intent.get("amount")
        self.options = []
        self.state = "IDLE"
        if "name_ar" in pick:  # a biller
            if not amount:
                reply.messages.append(f"شلون تريد تدفع لـ{pick['name_ar']}؟")
                self.state = "AWAITING_AMOUNT"
                return reply
            return self._propose_bill(pick, int(amount), reply)
        else:  # a contact
            if not amount:
                reply.messages.append(f"شلون تريد تحول إلى {pick['name']}؟")
                self.state = "AWAITING_AMOUNT"
                return reply
            return self._propose_transfer(pick, int(amount), reply)

    # ------------------------------------------------------------------ #
    def _handle_amount(self, text: str) -> Reply:
        reply = Reply()
        clean = text.strip()
        if CANCEL_WORDS.search(clean):
            self.state = "IDLE"
            self.pending_intents = []
            self.proposals = []
            reply.messages.append("تم الإلغاء. ما انحولّ شي.")
            return reply
        amount = self._parse_amount(text)
        if amount is None:
            reply.messages.append("ما فهمت المبلغ. اكتب الرقم بالدينار، مثلاً: 50000")
            return reply
        intent = self.current_intent or {}
        action = intent.get("action")
        if action == "transfer":
            name = intent.get("recipient")
            matches = self.wallet.search_contacts(self.user_id, name)
            res = resolve_contact(matches, name)
            if res["status"] != "unique":
                reply.messages.append("ضاع الاسم مني. ابدأ الطلب من جديد لو سمحت.")
                self.state = "IDLE"
                return reply
            return self._propose_transfer(res["contact"], amount, reply)
        if action == "bill_pay":
            biller_name = intent.get("biller")
            billers = self.wallet.search_billers(self.user_id, biller_name)
            res = resolve_biller(billers, biller_name)
            if res["status"] != "unique":
                reply.messages.append("ضاعت الشركة مني. ابدأ الطلب من جديد لو سمحت.")
                self.state = "IDLE"
                return reply
            return self._propose_bill(res["biller"], amount, reply)
        reply.messages.append("ضاع الطلب مني. ابدأ من جديد لو سمحت.")
        self.state = "IDLE"
        return reply

    @staticmethod
    def _parse_amount(text: str) -> int | None:
        clean = text.strip().replace(",", "").replace("،", "")
        m = re.search(r"(\d+(?:\.\d+)?)", clean)
        if not m:
            return None
        return int(float(m.group(1)))
