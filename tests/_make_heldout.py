"""Materializes tests/testset_heldout.json — the HELD-OUT evaluation set.

Written AFTER development froze: these requests were never used for tuning,
never run against the system during iteration, and are only executed for the
final honest report (tests/results_heldout.md). Fresh names, amounts, and
phrasings not present in the tuning set (tests/testset_iraqi.json).
Run:  py tests/_make_heldout.py
"""

import json
from pathlib import Path

OUT = Path(__file__).parent / "testset_heldout.json"

C = []


def case(id, category, turns, nlu, balance_delta=0, txn_count=0):
    C.append(
        {
            "id": id,
            "category": category,
            "turns": turns,
            "nlu": nlu,
            "wallet_expect": {"balance_delta": balance_delta, "txn_count": txn_count},
        }
    )


# simple transfer with different amount/name than tuning set
case(
    "H01",
    "heldout_transfer",
    [
        {"text": "حول لي 45000 لفاطمة", "expect": "ask_confirm"},
        {"text": "اكيد", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 45000, "recipient": "فاطمة"}]}],
    -45000,
    1,
)

# Iraqi slang for internet ("النت")
case(
    "H02",
    "heldout_bill_slang",
    [
        {"text": "سدد فاتورة النت 25000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "bill_pay", "amount": 25000, "biller": "انترنت"}]}],
    -25000,
    1,
)

# unique single-word contact that could be confused with a compound name
case(
    "H03",
    "heldout_transfer",
    [
        {"text": "ابعت 60000 لحسين", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 60000, "recipient": "حسين"}]}],
    -60000,
    1,
)

# ambiguity with an explicit pick of the third option
case(
    "H04",
    "heldout_ambiguous",
    [
        {"text": "حول 200000 لاحمد", "expect": "ask_disambiguation"},
        {"text": "3", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 200000, "recipient": "أحمد"}]}],
    -200000,
    1,
)

# insufficient funds
case(
    "H05",
    "heldout_insufficient",
    [{"text": "ادفع فاتورة الكهرباء 600000", "expect": "rejected_insufficient"}],
    [{"intents": [{"action": "bill_pay", "amount": 600000, "biller": "كهرباء"}]}],
)

# two-in-one with both amounts stated
case(
    "H06",
    "heldout_two_in_one",
    [
        {"text": "عبئ كورك 12000 وادفع فاتورة المي 7000", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed_both"},
    ],
    [
        {
            "intents": [
                {"action": "bill_pay", "amount": 12000, "biller": "كورك"},
                {"action": "bill_pay", "amount": 7000, "biller": "ماء"},
            ]
        }
    ],
    -19000,
    2,
)

# partial name that must resolve to the compound contact
case(
    "H07",
    "heldout_partial_name",
    [
        {"text": "حول مية الف لمحمد", "expect": "ask_confirm"},
        {"text": "نعم", "expect": "executed"},
    ],
    [{"intents": [{"action": "transfer", "amount": 100000, "recipient": "محمد"}]}],
    -100000,
    1,
)

# missing biller -> must ask
case(
    "H08",
    "heldout_missing_biller",
    [{"text": "دفع فاتورة", "expect": "ask_which_biller"}],
    [{"intents": [{"action": "bill_pay", "amount": None, "biller": None}]}],
)

# nonsense
case(
    "H09",
    "heldout_nonsense",
    [{"text": "خمشة", "expect": "clarify"}],
    [{"intents": [{"action": "unknown"}]}],
)

# refuse at confirmation
case(
    "H10",
    "heldout_refuse",
    [
        {"text": "حول 80000 لزينب", "expect": "ask_confirm"},
        {"text": "لا بعدين", "expect": "cancelled"},
    ],
    [{"intents": [{"action": "transfer", "amount": 80000, "recipient": "زينب"}]}],
)

data = {
    "_meta": {
        "description": (
            "HELD-OUT evaluation set: written after development froze, "
            "never used for tuning, run once for honest reporting "
            "(tests/results_heldout.md). Same schema as the tuning set."
        ),
        "user": "u1",
        "starting_balance": 450000,
    },
    "cases": C,
}

OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"written: {OUT}  ({len(C)} held-out cases)")
