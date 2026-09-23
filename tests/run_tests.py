"""Test harness for the Bill Pay & Transfer Agent.

Runs every case in tests/testset_iraqi.json end-to-end through the real state
machine + wallet API, and verifies BOTH the conversation behavior and the
wallet invariants (balance delta, number of new transactions) after each case.

Modes:
  --live   : use the real GLM-5.3 NLU (requires GLM_API_KEY in .env)
  --replay : use the recorded NLU outputs in the test set (deterministic,
             no API key needed) — the default when no key is configured.

Prerequisite: the wallet API must be running:
  py -m uvicorn wallet_api.main:app --port 8001

Run:  py tests/run_tests.py [--live|--replay]
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# load .env before importing agent (which reads env at call time)
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from agent import nlu  # noqa: E402
from agent.executor import WalletClient  # noqa: E402
from agent.session import Session  # noqa: E402

WALLET_BASE = os.environ.get("WALLET_URL", "http://127.0.0.1:8001")
USER_ID = os.environ.get("WALLET_USER_ID", "u1")
START_BALANCE = 450000
SEED_TXN_PREFIX = "t0"  # seed transaction ids start with this


# --------------------------------------------------------------------- #
# expectation predicates


def _any(reply, needle):
    return any(needle in m for m in reply.messages)


CHECKS = {
    "ask_confirm": lambda s, r: bool(r.cards) or s.state == "AWAITING_CONFIRMATION",
    "executed": lambda s, r: bool(r.executed) and all(e["ok"] for e in r.executed),
    "executed_both": lambda s, r: (
        len(r.executed) == 2 and all(e["ok"] for e in r.executed)
    ),
    "cancelled": lambda s, r: (
        not any(e.get("ok") for e in r.executed)
        and (_any(r, "الإلغاء") or _any(r, "انحول"))
    ),
    "not_executed": lambda s, r: not any(e.get("ok") for e in r.executed),
    "ask_disambiguation": lambda s, r: r.choices is not None,
    "ask_amount": lambda s, r: s.state == "AWAITING_AMOUNT" or _any(r, "شلون"),
    "ask_recipient": lambda s, r: _any(r, "لمين"),
    "ask_which_biller": lambda s, r: _any(r, "أي فاتورة"),
    "clarify": lambda s, r: (
        s.state == "IDLE"
        and not r.cards
        and not any(e.get("ok") for e in r.executed)
        and bool(r.messages)
    ),
    "rejected_insufficient": lambda s, r: _any(r, "ما يكفي"),
    "contact_not_found": lambda s, r: _any(r, "ما ألقى اسم"),
    "biller_not_found": lambda s, r: _any(r, "ما ألقى شركة"),
    "balance_reported": lambda s, r: _any(r, "رصيدك الحالي"),
    "history_reported": lambda s, r: _any(r, "آخر الحركات"),
}


def check_expect(session, reply, expect: str) -> tuple[bool, str]:
    for code in expect.split("|"):
        code = code.strip()
        fn = CHECKS.get(code)
        if fn is None:
            return False, f"unknown expectation '{code}'"
        if fn(session, reply):
            return True, code
    return False, "none of the alternatives matched"


# --------------------------------------------------------------------- #
# wallet helpers


def reset_wallet():
    httpx.post(f"{WALLET_BASE}/admin/reset", timeout=10).raise_for_status()


def wallet_state() -> dict:
    user = httpx.get(f"{WALLET_BASE}/users/{USER_ID}", timeout=10).json()
    txns = httpx.get(
        f"{WALLET_BASE}/users/{USER_ID}/transactions", params={"limit": 100}, timeout=10
    ).json()
    new_txns = [t for t in txns if not t["id"].startswith(SEED_TXN_PREFIX)]
    return {"balance": user["balance_iqd"], "new_txns": new_txns}


# --------------------------------------------------------------------- #
# API idempotency scripts (wallet-level, bypassing the chat)


def script_double_transfer_same_key(wallet: WalletClient) -> tuple[bool, str]:
    reset_wallet()
    key = "test-key-same-1"
    r1 = wallet.transfer(USER_ID, "c7", 25000, key)
    r2 = wallet.transfer(USER_ID, "c7", 25000, key)
    st = wallet_state()
    ok = (
        r1.get("ok")
        and r2.get("ok")
        and r1["transaction_id"] == r2["transaction_id"]
        and r2.get("duplicate") is True
        and st["balance"] == START_BALANCE - 25000
        and len(st["new_txns"]) == 1
    )
    return ok, (
        f"txn={r1.get('transaction_id')} dup={r2.get('duplicate')} "
        f"balance={st['balance']} txns={len(st['new_txns'])}"
    )


def script_executor_retry_same_key(wallet: WalletClient) -> tuple[bool, str]:
    reset_wallet()
    key = "test-key-retry-1"
    r1 = wallet.transfer(USER_ID, "c10", 10000, key)
    r2 = wallet.transfer(USER_ID, "c10", 10000, key)  # simulated retry (same key)
    st = wallet_state()
    ok = (
        r2.get("duplicate") is True
        and st["balance"] == START_BALANCE - 10000
        and len(st["new_txns"]) == 1
    )
    return ok, f"retry flagged duplicate, single debit: balance={st['balance']}"


def script_legit_two_transfers(wallet: WalletClient) -> tuple[bool, str]:
    reset_wallet()
    r1 = wallet.transfer(USER_ID, "c7", 20000, "test-key-A")
    r2 = wallet.transfer(USER_ID, "c7", 20000, "test-key-B")
    st = wallet_state()
    ok = (
        r1.get("ok")
        and r2.get("ok")
        and r1["transaction_id"] != r2["transaction_id"]
        and st["balance"] == START_BALANCE - 40000
        and len(st["new_txns"]) == 2
    )
    return ok, f"two distinct txns, balance={st['balance']}"


SCRIPTS = {
    "double_transfer_same_key": script_double_transfer_same_key,
    "executor_retry_same_key": script_executor_retry_same_key,
    "legit_two_transfers": script_legit_two_transfers,
}


# --------------------------------------------------------------------- #


def run(
    mode: str, testfile: str = "testset_iraqi.json", outfile: str = "results.md"
) -> int:
    testset = json.loads((ROOT / "tests" / testfile).read_text(encoding="utf-8"))
    cases = testset["cases"]

    wallet = WalletClient(WALLET_BASE)
    results = []

    if mode == "replay":
        original = nlu.extract_intents

        def fake_extract(text, history=None):
            raise RuntimeError(
                "replay queue exhausted (NLU called more times than recorded)"
            )

        # per-case queue is installed right before each case
        nlu.extract_intents = fake_extract
    else:
        if not os.environ.get("GLM_API_KEY"):
            print("GLM_API_KEY not set — cannot run live mode.")
            return 2

    for case in cases:
        if "script" in case:
            ok, detail = SCRIPTS[case["script"]](wallet)
            results.append((case, ok, [], detail))
            continue

        # replay: install this case's recorded NLU queue
        if mode == "replay":
            queue = list(case.get("nlu", []))

            def queued_extract(text, history=None, _q=queue):
                if not _q:
                    raise RuntimeError("replay queue exhausted")
                return _q.pop(0)

            nlu.extract_intents = queued_extract

        reset_wallet()
        session = Session(USER_ID, wallet, session_id=uuid.uuid4().hex[:12])
        turn_results = []
        fail_note = ""
        try:
            for turn in case["turns"]:
                reply = session.handle(turn["text"])
                ok, note = check_expect(session, reply, turn["expect"])
                turn_results.append((turn["expect"], ok))
                if not ok:
                    fail_note = (
                        f"turn '{turn['text']}' expected {note}, got: "
                        + " | ".join(reply.messages[:2])
                        + f" [state={session.state}]"
                    )
                    break
        except Exception as e:
            turn_results.append((turn.get("expect", "?"), False))
            fail_note = f"exception: {e}"

        # wallet invariants (only meaningful if all turns matched)
        st = wallet_state()
        wx = case.get("wallet_expect", {})
        invariant_ok = True
        detail = f"balance={st['balance']} new_txns={len(st['new_txns'])}"
        if all(ok for _, ok in turn_results):
            if (
                "balance_delta" in wx
                and st["balance"] != START_BALANCE + wx["balance_delta"]
            ):
                invariant_ok = False
                detail = (
                    f"balance {st['balance']} != {START_BALANCE + wx['balance_delta']}"
                )
            if "txn_count" in wx and len(st["new_txns"]) != wx["txn_count"]:
                invariant_ok = False
                detail = f"new_txns {len(st['new_txns'])} != {wx['txn_count']}"
        results.append(
            (
                case,
                all(ok for _, ok in turn_results) and invariant_ok,
                turn_results,
                fail_note or detail,
            )
        )

    if mode == "replay":
        nlu.extract_intents = original

    # ---------------- report ----------------
    total = len(results)
    passed = sum(1 for _, ok, _, _ in results if ok)
    cats = {}
    for case, ok, _, _ in results:
        c = case["category"]
        p, f = cats.get(c, (0, 0))
        cats[c] = (p + (1 if ok else 0), f + (0 if ok else 1))

    print(
        f"\n{'=' * 64}\n  RESULTS: {passed}/{total} passed  (mode: {mode.upper()})\n{'=' * 64}"
    )
    for cat in sorted(cats):
        p, f = cats[cat]
        print(f"  {cat:<28} {'PASS' if f == 0 else 'FAIL':<6} {p}/{p + f}")
    fails = [(c, n) for c, ok, _, n in results if not ok]
    if fails:
        print(f"\n  FAILURES ({len(fails)}):")
        for case, note in fails:
            print(f"   - {case['id']} [{case['category']}]: {note}")
    print()

    # markdown report
    lines = [
        "# Test Results — Bill Pay & Transfer Agent",
        "",
        f"- Date: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Mode: **{mode.upper()}** "
        + (
            "(real GLM-5.3 NLU)"
            if mode == "live"
            else "(recorded NLU, deterministic core)"
        ),
        f"- Test set: {total} cases (55 Iraqi-dialect chat cases + 3 wallet idempotency scripts)",
        f"- Starting balance per case: {START_BALANCE:,} IQD (wallet reset before each case)",
        "",
        "## Summary",
        "",
        "| Category | Pass | Fail |",
        "|---|---|---|",
    ]
    for cat in sorted(cats):
        p, f = cats[cat]
        lines.append(f"| {cat} | {p} | {f} |")
    lines += [
        "",
        f"**Total: {passed}/{total} passed ({100 * passed / total:.0f}%)**",
        "",
        "## Cases",
        "",
        "| ID | Category | First request | Expected outcome | Result | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for case, ok, turns, note in results:
        first = case["turns"][0]["text"] if "turns" in case else case.get("desc", "")
        expects = " → ".join(
            f"`{t}`"
            for t in (
                [case["turns"][i]["expect"] for i in range(1)]
                if "turns" in case
                else []
            )
        ) or case.get("desc", "")
        all_expects = ", ".join(t["expect"] for t in case.get("turns", [])) or case.get(
            "script", ""
        )
        lines.append(
            f"| {case['id']} | {case['category']} | {first} | {all_expects} | "
            f"{'PASS' if ok else 'FAIL'} | {note} |"
        )
    (ROOT / "tests" / outfile).write_text("\n".join(lines), encoding="utf-8")
    print(f"report written: tests/{outfile}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    mode = "replay"
    testfile, outfile = "testset_iraqi.json", "results.md"
    it = iter(args)
    for a in it:
        if a == "--live":
            mode = "live"
        elif a == "--replay":
            mode = "replay"
        elif a == "--file":
            testfile = next(it)
            outfile = testfile.replace("testset_", "results_").replace(".json", ".md")
    if not [a for a in args if a in ("--live", "--replay")]:
        mode = "live" if os.environ.get("GLM_API_KEY") else "replay"
    # health check
    try:
        httpx.get(f"{WALLET_BASE}/health", timeout=5)
    except Exception:
        print(f"wallet API not reachable at {WALLET_BASE}.")
        print("start it first:  py -m uvicorn wallet_api.main:app --port 8001")
        sys.exit(2)
    sys.exit(run(mode, testfile, outfile))
