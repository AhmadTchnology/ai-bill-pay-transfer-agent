"""One-time generator for tests/testset_iraqi.json.

The test requests were drafted with an LLM (GLM-5.3) from the categories below,
then hand-edited for realistic Iraqi dialect. This script materializes the
hand-edited set as JSON so the harness can consume it.
Run:  py tests/_make_testset.py
"""

import json
from pathlib import Path

OUT = Path(__file__).parent / "testset_iraqi.json"

C = []  # cases


def case(id, category, turns, nlu, balance_delta=0, txn_count=0, **extra):
    c = {
        "id": id,
        "category": category,
        "turns": turns,
        "nlu": nlu,
        "wallet_expect": {"balance_delta": balance_delta, "txn_count": txn_count},
    }
    c.update(extra)
    C.append(c)


# ---------------- simple transfers ----------------
case(
    "T01",
    "simple_transfer",
    [
        {"text": "حول 50000 لزينب", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 50000, "recipient": "زينب"}]}],
    -50000,
    1,
)
case(
    "T02",
    "simple_transfer",
    [
        {"text": "ابعت 25000 لمحمد الجبوري", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [
        {
            "intents": [
                {"action": "transfer", "amount": 25000, "recipient": "محمد الجبوري"}
            ]
        }
    ],
    -25000,
    1,
)
case(
    "T03",
    "simple_transfer",
    [
        {"text": "حول لي 100000 لنور", "expect": "ask_confirm"},
        {"text": "اكيد", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 100000, "recipient": "نور"}]}],
    -100000,
    1,
)
case(
    "T04",
    "simple_transfer",
    [
        {"text": "سوي تحويل 75000 لفاطمة", "expect": "ask_confirm"},
        {"text": "ايوة", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 75000, "recipient": "فاطمة"}]}],
    -75000,
    1,
)
case(
    "T05",
    "simple_transfer",
    [
        {"text": "دز 12000 لعمر التميمي", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [
        {
            "intents": [
                {"action": "transfer", "amount": 12000, "recipient": "عمر التميمي"}
            ]
        }
    ],
    -12000,
    1,
)
case(
    "T06",
    "simple_transfer",
    [
        {"text": "حول مية الف لمريم عبد الله", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [
        {
            "intents": [
                {"action": "transfer", "amount": 100000, "recipient": "مريم عبد الله"}
            ]
        }
    ],
    -100000,
    1,
)
case(
    "T07",
    "simple_transfer",
    [
        {"text": "ابعت 15000 للدكتورة ليلى", "expect": "ask_confirm"},
        {"text": "زين", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 15000, "recipient": "د. ليلى"}]}],
    -15000,
    1,
)
case(
    "T08",
    "simple_transfer",
    [
        {"text": "كمل حوالة 30000 لكرار", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 30000, "recipient": "كرار"}]}],
    -30000,
    1,
)

# ---------------- bill payments ----------------
case(
    "T09",
    "bill_missing_amount",
    [
        {"text": "دفع فاتورة الكهرباء", "expect": "ask_amount"},
        {"text": "35000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": None, "biller": "كهرباء"}]}],
    -35000,
    1,
)
case(
    "T10",
    "simple_bill",
    [
        {"text": "سدد فاتورة الماء 8000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 8000, "biller": "ماء"}]}],
    -8000,
    1,
)
case(
    "T11",
    "simple_bill",
    [
        {"text": "دفع انترنت الفردوس 30000", "expect": "ask_confirm"},
        {"text": "اكيد", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 30000, "biller": "انترنت"}]}],
    -30000,
    1,
)
case(
    "T12",
    "simple_bill",
    [
        {"text": "شحن رصيد آسياسيل 15000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 15000, "biller": "آسياسيل"}]}],
    -15000,
    1,
)
case(
    "T13",
    "simple_bill",
    [
        {"text": "شحن زين العراق 20000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 20000, "biller": "زين العراق"}]}],
    -20000,
    1,
)
case(
    "T14",
    "simple_bill",
    [
        {"text": "عبئ كورك 10000", "expect": "ask_confirm"},
        {"text": "ايوة", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 10000, "biller": "كورك"}]}],
    -10000,
    1,
)
case(
    "T15",
    "simple_bill",
    [
        {"text": "ادفع فاتورة المي 12000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 12000, "biller": "ماء"}]}],
    -12000,
    1,
)

# ---------------- ambiguity ----------------
case(
    "T16",
    "ambiguous_contact",
    [
        {"text": "حول 50000 لأحمد", "expect": "ask_disambiguation"},
        {"text": "2", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 50000, "recipient": "أحمد"}]}],
    -50000,
    1,
)
case(
    "T17",
    "ambiguous_contact",
    [
        {"text": "ابعت 20000 لعلي", "expect": "ask_disambiguation"},
        {"text": "1", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 20000, "recipient": "علي"}]}],
    -20000,
    1,
)
case(
    "T18",
    "ambiguous_resolved_specific",
    [
        {"text": "حول 30000 لأحمد حسين", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 30000, "recipient": "أحمد حسين"}]}],
    -30000,
    1,
)
case(
    "T19",
    "ambiguous_resolved_specific",
    [
        {"text": "ابعت 70000 لاحمد علي", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 70000, "recipient": "أحمد علي"}]}],
    -70000,
    1,
)

# ---------------- missing info ----------------
case(
    "T20",
    "missing_recipient",
    [
        {"text": "حول 20000", "expect": "ask_recipient"},
        {"text": "لزينب", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [
        {"intents": [{"action": "transfer", "amount": 20000, "recipient": None}]},
        {"intents": [{"action": "transfer", "amount": None, "recipient": "زينب"}]},
    ],
    -20000,
    1,
)
case(
    "T21",
    "missing_biller",
    [{"text": "دفع فاتورة", "expect": "ask_which_biller"}],
    [{"intents": [{"action": "bill_pay", "amount": None, "biller": None}]}],
)

# ---------------- malformed / unclear ----------------
for i, txt in [
    (22, "ابعت شي"),
    (23, "حول"),
    (24, "سدد"),
    (32, "شنو هذا؟"),
    (33, "احجبنة فلوت احه"),
    (34, "هههههه"),
    (35, "458"),
    (36, "توك تؤبرني"),
    (44, "شكرا چبي"),
]:
    case(
        f"T{i}",
        "malformed" if i != 44 else "smalltalk",
        [{"text": txt, "expect": "clarify"}],
        [{"intents": [{"action": "unknown"}]}],
    )

# ---------------- insufficient funds ----------------
case(
    "T25",
    "insufficient_funds",
    [{"text": "حول 900000 لزينب", "expect": "rejected_insufficient"}],
    [{"intents": [{"action": "transfer", "amount": 900000, "recipient": "زينب"}]}],
)
case(
    "T26",
    "insufficient_funds",
    [{"text": "دفع فاتورة كهرباء 500000", "expect": "rejected_insufficient"}],
    [{"intents": [{"action": "bill_pay", "amount": 500000, "biller": "كهرباء"}]}],
)
case(
    "T27",
    "insufficient_funds_combined",
    [
        {
            "text": "حول 400 الف لزينب وادفع فاتورة الكهرباء 100 الف",
            "expect": "rejected_insufficient",
        }
    ],
    [
        {
            "intents": [
                {"action": "transfer", "amount": 400000, "recipient": "زينب"},
                {"action": "bill_pay", "amount": 100000, "biller": "كهرباء"},
            ]
        }
    ],
)

# ---------------- unknowns ----------------
case(
    "T28",
    "unknown_contact",
    [{"text": "حول 25000 لسيف", "expect": "contact_not_found"}],
    [{"intents": [{"action": "transfer", "amount": 25000, "recipient": "سيف"}]}],
)
case(
    "T29",
    "unknown_biller",
    [{"text": "ادفع فاتورة النجرة", "expect": "biller_not_found"}],
    [{"intents": [{"action": "bill_pay", "amount": 20000, "biller": "نجرة"}]}],
)
case(
    "T30",
    "unknown_biller",
    [{"text": "شحن رصيد اورنج 15000", "expect": "biller_not_found"}],
    [{"intents": [{"action": "bill_pay", "amount": 15000, "biller": "اورنج"}]}],
)
case(
    "T31",
    "unlinked_biller",
    [{"text": "ادفع فاتورة غاز المدينة 20000", "expect": "biller_not_found"}],
    [{"intents": [{"action": "bill_pay", "amount": 20000, "biller": "غاز المدينة"}]}],
)

# ---------------- two requests in one sentence ----------------
case(
    "T37",
    "two_in_one",
    [
        {"text": "دفع فاتورة الكهرباء وابعت 10000 لزينب", "expect": "ask_amount"},
        {"text": "35000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed_both"},
    ],
    [
        {
            "intents": [
                {"action": "bill_pay", "amount": None, "biller": "كهرباء"},
                {"action": "transfer", "amount": 10000, "recipient": "زينب"},
            ]
        }
    ],
    -45000,
    2,
)
case(
    "T38",
    "two_in_one",
    [
        {"text": "حول 20000 لنور وشحن كورك 10000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed_both"},
    ],
    [
        {
            "intents": [
                {"action": "transfer", "amount": 20000, "recipient": "نور"},
                {"action": "bill_pay", "amount": 10000, "biller": "كورك"},
            ]
        }
    ],
    -30000,
    2,
)
case(
    "T39",
    "two_in_one_missing_amounts",
    [
        {"text": "سدد فاتورة الماء وادفع الانترنت", "expect": "ask_amount"},
        {"text": "8000", "expect": "ask_amount"},
        {"text": "30000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed_both"},
    ],
    [
        {
            "intents": [
                {"action": "bill_pay", "amount": None, "biller": "ماء"},
                {"action": "bill_pay", "amount": None, "biller": "انترنت"},
            ]
        }
    ],
    -38000,
    2,
)

# ---------------- queries ----------------
case(
    "T40",
    "query",
    [{"text": "كم رصيدي؟", "expect": "balance_reported"}],
    [{"intents": [{"action": "balance_check"}]}],
)
case(
    "T41",
    "query",
    [{"text": "شو آخر حركاتك؟", "expect": "history_reported"}],
    [{"intents": [{"action": "history"}]}],
)
case(
    "T42",
    "query",
    [{"text": "شنو رصيد المحفظة؟", "expect": "balance_reported"}],
    [{"intents": [{"action": "balance_check"}]}],
)
case(
    "T43",
    "query_flexible",
    [
        {
            "text": "وين تروح فلوسي؟",
            "expect": "balance_reported|history_reported|clarify",
        }
    ],
    [{"intents": [{"action": "history"}]}],
)

# ---------------- cancel / should-not-execute flows ----------------
case(
    "T45",
    "cancel_flow",
    [
        {"text": "حول 30000 لزينب", "expect": "ask_confirm"},
        {"text": "لا", "expect": "cancelled"},
    ],
    [{"intents": [{"action": "transfer", "amount": 30000, "recipient": "زينب"}]}],
)
case(
    "T46",
    "cancel_flow",
    [
        {"text": "دفع فاتورة كهرباء 35000", "expect": "ask_confirm"},
        {"text": "بعدين", "expect": "not_executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 35000, "biller": "كهرباء"}]}],
)
case(
    "T47",
    "cancel_flow",
    [
        {"text": "حول 30000 لزينب", "expect": "ask_confirm"},
        {"text": "لا زين", "expect": "cancelled"},
    ],
    [{"intents": [{"action": "transfer", "amount": 30000, "recipient": "زينب"}]}],
)
case(
    "T48",
    "cancel_flow",
    [
        {"text": "حول 50000 لأحمد", "expect": "ask_disambiguation"},
        {"text": "كنسل", "expect": "cancelled"},
    ],
    [{"intents": [{"action": "transfer", "amount": 50000, "recipient": "أحمد"}]}],
)
case(
    "T49",
    "cancel_flow",
    [
        {"text": "دفع فاتورة الكهرباء", "expect": "ask_amount"},
        {"text": "الغي", "expect": "cancelled"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": None, "biller": "كهرباء"}]}],
)
case(
    "T50",
    "repeat_transfer_legit",
    [
        {"text": "حول 50000 لزينب", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
        {"text": "حول 50000 لزينب", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [
        {"intents": [{"action": "transfer", "amount": 50000, "recipient": "زينب"}]},
        {"intents": [{"action": "transfer", "amount": 50000, "recipient": "زينب"}]},
    ],
    -100000,
    2,
)

# ---------------- more edge cases ----------------
case(
    "T51",
    "ambiguous_biller",
    [
        {"text": "شحن موبايل 15000", "expect": "ask_disambiguation"},
        {"text": "1", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 15000, "biller": "موبايل"}]}],
    -15000,
    1,
)
case(
    "T52",
    "confirm_english",
    [
        {"text": "حول 20000 لنور", "expect": "ask_confirm"},
        {"text": "yes", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 20000, "recipient": "نور"}]}],
    -20000,
    1,
)
case(
    "T53",
    "insufficient_after_payment",
    [
        {"text": "حول 400000 لزينب", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
        {"text": "ادفع فاتورة كهرباء 100000", "expect": "rejected_insufficient"},
    ],
    [
        {"intents": [{"action": "transfer", "amount": 400000, "recipient": "زينب"}]},
        {"intents": [{"action": "bill_pay", "amount": 100000, "biller": "كهرباء"}]},
    ],
    -400000,
    1,
)
case(
    "T54",
    "two_in_one_cancel",
    [
        {"text": "دفع فاتورة الكهرباء وابعت 10000 لزينب", "expect": "ask_amount"},
        {"text": "لا", "expect": "cancelled"},
    ],
    [
        {
            "intents": [
                {"action": "bill_pay", "amount": None, "biller": "كهرباء"},
                {"action": "transfer", "amount": 10000, "recipient": "زينب"},
            ]
        }
    ],
)
case(
    "T55",
    "history_after_payment",
    [
        {"text": "حول 20000 لزينب", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
        {"text": "شو آخر حركاتك؟", "expect": "history_reported"},
    ],
    [
        {"intents": [{"action": "transfer", "amount": 20000, "recipient": "زينب"}]},
        {"intents": [{"action": "history"}]},
    ],
    -20000,
    1,
)

# ---------------- idempotency (wallet-level, scripted) ----------------
C.append(
    {
        "id": "A01",
        "category": "api_idempotency",
        "script": "double_transfer_same_key",
        "desc": "same Idempotency-Key twice -> one debit, same transaction id",
    }
)
C.append(
    {
        "id": "A02",
        "category": "api_idempotency",
        "script": "executor_retry_same_key",
        "desc": "executor-level retry with same key -> duplicate flag, one debit",
    }
)
C.append(
    {
        "id": "A03",
        "category": "api_idempotency",
        "script": "legit_two_transfers",
        "desc": "different keys -> two debits (legitimate repeat still works)",
    }
)

data = {
    "_meta": {
        "description": (
            "Test set of Iraqi-dialect requests: drafted with an LLM (GLM-5.3) "
            "from category definitions, then hand-edited for realism. Includes "
            "ambiguous, malformed, insufficient-funds and should-not-execute "
            "cases. 'nlu' holds recorded NLU output per NLU-calling turn so the "
            "harness can replay deterministically without an API key; in live "
            "mode the real GLM-5.3 NLU is used instead."
        ),
        "user": "u1",
        "starting_balance": 450000,
    },
    "cases": C,
}

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"written: {OUT}")
print(
    f"total cases: {len(C)}  (chat: {sum(1 for c in C if 'script' not in c)}, api: {sum(1 for c in C if 'script' in c)})"
)
