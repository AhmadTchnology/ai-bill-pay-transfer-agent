# Bill Pay & Transfer Agent — وكيل دفع الفواتير والتحويل

Turns **"دفع فاتورة الكهرباء"** or **"حول 50 الف لأحمد"** (Iraqi Arabic, spoken or typed) into a completed, **confirmed** transaction against a mock wallet — or an honest explanation of why it couldn't be done.

Built for the AI Hackathon *"Bill Pay & Transfer Agent"* brief. No real payment systems are touched: the agent executes against a **mock wallet API** with contacts, billers, balances and transaction history.

**Read next:**
- `DISCLOSURE.md` — full disclosure of models, tools, data sources, and AI assistants used
- `FAILURE_MODES.md` — 8 documented failure modes and how each is handled
- `tests/results.md` — tuning-set results (58/58 live mode)
- `tests/results_heldout.md` — **held-out set results** (written after development froze)

---

## Problem & impact

Paying a bill or sending money in a wallet app takes many taps and several screens. Users who are less comfortable with smartphones — older relatives, first-time smartphone owners, people in a hurry — abandon the flow or make mistakes. In Iraq the friction is compounded because people **speak in dialect** while most interfaces expect formal Arabic or English.

This agent takes a single sentence, spoken or typed the way an Iraqi actually says it — "دفع فاتورة الكهرباء", "حول 50 الف لأحمد" — works out what's missing, **asks instead of guessing**, shows one readable confirmation, and either completes the payment or explains honestly why it couldn't.

> **User evidence:** the problem statement and target user come from the competition brief. *(Team note: add any interviews / observations with real wallet users here before final submission.)*

---

## Requirements → where they live

| Brief requirement | Implementation |
|---|---|
| Nothing executes without an explicit, readable confirmation | `agent/session.py` — a state machine; the LLM can only *propose*. Execution requires state `AWAITING_CONFIRMATION` **and** a rule-based (regex) "نعم" from the user. A hallucinated LLM intent can never move money alone. |
| Ambiguity is resolved by asking, not guessing | `agent/resolver.py` — two contacts named "أحمد" (plus "أحمد علي", "أحمد حسين") always produce a numbered question. A bare biller category ("موبايل" → آسياسيل/زين/كورك) also asks. |
| Retries never cause a double payment | Idempotency keys minted at **proposal** time (`agent/executor.py`), enforced by the wallet (`wallet_api/db.py` `idempotency_keys` table). Retries with the same key return the original result. Proven by API tests A01–A03. |
| Clear, honest failure messages | Typed failures everywhere: unknown contact, unknown/unlinked biller, insufficient funds (shows actual balance), wallet unreachable, half-of-two-part-request (never executes half). |
| Mock wallet with contacts (incl. duplicates), billers, balances, history | `data/seed_data.json` — LLM-generated from `data_gen/wallet_schema.json`, hand-edited. 15 contacts (deliberate Ahmed/Ali/Hussein near-duplicates), 7 billers, 6 linked, transaction history. |
| Test set: 50+ Iraqi-dialect requests incl. ambiguous/malformed, LLM-generated then hand-edited | `tests/testset_iraqi.json` — 55 chat cases + 3 wallet idempotency scripts, generated via `tests/_make_testset.py` (drafted with GLM-5.3 from category definitions, then hand-edited for realism). |
| Test results, incl. behavior on requests that should not go through | `tests/results.md` — tuning set, **58/58 PASS in live mode** (real GLM-5.3 NLU). Plus a **held-out set** (`tests/testset_heldout.json`, 10 cases written after development froze, never used for tuning) with honest results in `tests/results_heldout.md`. |
| Edge cases: insufficient balance, unknown contact, a request that is really two requests | Covered by test categories `insufficient_funds*`, `unknown_contact`, `two_in_one*` (one card lists both, one "نعم" executes both, "لا" cancels both). |
| **Stretch:** voice input in spoken Iraqi Arabic | **Done and verified.** `voice/stt.py` — faster-whisper `large-v3-turbo` (int8) with Iraqi-dialect `initial_prompt` + hotwords for short confirm words. The browser 🎙 button uploads webm/opus → `/api/voice` → transcript → **the same text pipeline and confirmation rules — voice can never skip the "نعم"**. End-to-end evidence: `tests/voice_smoke.py` — **6/6 PASS** (spoken transfer → card → spoken "نعم" → single debit; spoken ambiguous "أحمد" → question; spoken bill → asks amount; spoken balance query → reports balance). |

---

## Architecture

```
 typed text ─────────────┐
                          ▼
 voice (stretch) → faster-whisper (large-v3-turbo, int8)
                          │ text
                          ▼
                GLM-5.3 NLU (agent/nlu.py)          ← the LLM only PROPOSES:
                          │  structured intents      {action, amount, recipient, biller}
                          ▼
                State machine (agent/session.py)
                   ├─ resolve contact/biller (agent/resolver.py — ask, never guess)
                   ├─ missing info? → ask (amount / who / which)
                   └─ all resolved? → confirmation card
                                        │ user replies "نعم" (regex-checked)
                                        ▼
                Executor (agent/executor.py)        ← the ONLY code that moves money;
                   │  Idempotency-Key per proposal    retries reuse the key
                   ▼
                Mock Wallet API (wallet_api/ — FastAPI + SQLite)
                   ├─ dedupes on (key, user)
                   ├─ atomic debit + txn insert (BEGIN IMMEDIATE)
                   └─ typed, honest errors
                          │
                          ▼
                result reported back in Arabic
```

### Why the confirmation step is designed, not bolted on

1. **The LLM has no execution power.** NLU returns plain JSON; it holds no wallet credentials and no tool to call. The only path to `POST /transfers` is `_execute_proposals()`, reached exclusively from `AWAITING_CONFIRMATION` + rule-based yes.
2. **The card shows the right information at the right moment**: recipient (with phone/bank), biller (with account number), each amount, balance before → after. For two-in-one requests, ALL proposals appear on one card — you approve exactly what you read.
3. **Cancel words are checked before confirm words** — "لا زين" is a cancel, not a "زين".
4. **Anything that isn't an explicit yes is a no**: an unclear reply drops the pending transaction with "ما انحولّ شي".
5. The wallet enforces idempotency *in addition*, so even a bug or a network retry cannot double-pay.

### How retries can't double-pay (the short version)

- Each proposal gets `Idempotency-Key = sha256(session_id, proposal_nonce)` **when the card is created**.
- The executor retries failed HTTP calls with the **same key**; the wallet persists `key → transaction`, so a retry after a timeout returns the original result (`duplicate: true`) instead of paying again.
- A *new* request (new proposal ⇒ new nonce ⇒ new key) legitimately transfers again — tested by T50.

---

## Running it

Prerequisites: Python 3.10+ (3.12 tested), then:

```bat
py -m pip install -r requirements.txt
copy .env.example .env      :: put your GLM endpoint + key here
```

**One-click demo** (starts wallet API + web UI, opens the browser):

```bat
run_demo.bat
```

Or manually, in two terminals:

```bat
py -m uvicorn wallet_api.main:app --port 8001     :: mock wallet
py -m uvicorn web.app:app --port 8000             :: agent + chat UI → http://127.0.0.1:8000
```

**Tests:**

```bat
py tests/run_tests.py            :: replay mode (no API key needed, deterministic)
py tests/run_tests.py --live     :: full E2E with the real GLM-5.3 NLU
```

The harness resets the wallet before every case and verifies both the conversation behavior **and** wallet invariants (balance delta, transaction count).

**Voice (stretch — done and verified):** `pip install faster-whisper`, then use the 🎙 button in the chat. First run downloads the model (~1.6 GB, int8 ≈ 2 GB RAM). Reproduce our voice evidence:

```bat
py tests\make_voice_fixtures.py   :: Iraqi-voice fixtures (edge-tts, ar-IQ)
py tests\voice_smoke.py           :: 6/6 — spoken transfer/confirm/ambiguity/bill/balance
```

The browser mic records webm/opus; the smoke test uploads exactly that container/codec, so it exercises the real mic path without needing a live microphone.

---

## Data generation methodology

Per the brief, mock data and test set were **generated with an LLM from schemas we define**, then hand-edited:

- `data_gen/wallet_schema.json` + `data_gen/prompts.md` — the schema and the prompts used to generate the wallet contents (deliberately including duplicate/similar contact names).
- `tests/_make_testset.py` — the category definitions the test requests were generated from (drafts by GLM-5.3, hand-edited for dialect realism), and the generator that materializes `tests/testset_iraqi.json`.

## Project layout

```
wallet_api/        mock wallet API (FastAPI + SQLite, idempotent money endpoints)
agent/             NLU (GLM-5.3), resolver, confirmation state machine, executor
web/               chat UI backend + static RTL Arabic frontend
voice/             stretch: faster-whisper STT wired into the same pipeline
tests/             Iraqi-dialect test set, harness, results.md
data/              seed wallet data (LLM-generated from schema, hand-edited)
data_gen/          data schemas + LLM generation prompts
```

## Honest limitations

- The NLU is a probabilistic component: live-mode accuracy depends on GLM-5.3; the replay suite pins the deterministic core to 58/58.
- Arabic fuzzy name matching uses normalization + similarity scores; exotic spellings may still ask "لمين؟" — which is the intended safe behavior.
- No real banking integration (out of scope by design); the mock wallet is the execution boundary.
