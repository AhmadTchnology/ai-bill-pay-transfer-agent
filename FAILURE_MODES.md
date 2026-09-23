# Documented Failure Modes & How the System Handles Them

The brief asks for at least three documented failure modes. Here are **eight** we designed for, each verified by an automated test in `tests/run_tests.py` (case IDs referenced).

## 1. Ambiguous recipient — "which Ahmed?" (T16, T17, T51)

**Failure:** The user says "حول 50 الف لأحمد", but the wallet has *أحمد*, *أحمد علي* and *أحمد حسين*.

**Handling:** Never guess. The resolver (`agent/resolver.py`) detects that the query is a prefix of multiple names and the state machine asks a numbered question with phones/banks so the user can tell them apart. Only an explicit pick continues the flow. A bare biller category ("موبايل" → آسياسيل/زين/كورك) gets the same treatment (T51).

## 2. Insufficient balance (T25, T26, T27, T53)

**Failure:** The requested amount exceeds the available balance — including *after* an earlier payment in the same session, or when a two-part request costs more than the balance combined.

**Handling:** The proposal stage checks `available = balance − pending proposals` **before** showing any card and rejects early with an honest message that shows the actual available amount and the requested amount. For multi-intent requests, **the entire request is dropped** — half a request is never executed (T27). The wallet re-checks atomically at execution time, so the pre-check is UX, not the safety net.

## 3. Unknown or unlinked payee (T28, T29, T30, T31)

**Failure:** "حول 25000 لسيف" (no such contact), "ادفع فاتورة النجرة" (no such biller), "غاز المدينة" (a real biller the user never linked).

**Handling:** The agent reports exactly what it couldn't find, and — where a list exists — shows the registered contacts/billers so the user can recover without restarting. It never substitutes a different recipient or biller (the NLU prompt forbids inventing names, and the resolver rejects what it can't match).

## 4. Unclear / malformed input (T22–T36, T44)

**Failure:** "ابعت شي", "احجبنة فلوت احه", "458", "توك تؤبرني", smalltalk.

**Handling:** The NLU returns `unknown` rather than inventing an intent; the agent asks for a well-formed request. No intent → no proposal → nothing can execute.

## 5. Missing information (T09, T20, T21, T39)

**Failure:** Amount, recipient or biller missing: "دفع فاتورة الكهرباء", "حول 20000".

**Handling:** The state machine asks for the missing piece. Amounts stated before the recipient ("حول 20000" → "لزينب") are carried over deterministically by the session — not left to the LLM's memory. For two-in-one requests with missing amounts, the agent asks for each before showing one combined card (T39).

## 6. Confirmation skipped, refused, or vague (T45–T49, T54)

**Failure:** The user answers anything other than an explicit "نعم" — "لا", "لا زين", "كنسل", "بعدين", or gibberish — or tries to skip the confirmation.

**Handling:** Cancel words are matched **before** confirm words ("لا زين" is a cancel). Anything that isn't an explicit confirm word drops all pending proposals with "ما انحولّ شي". This check is a **rule-based regex, not the LLM** — a hallucinated yes can't move money. Multi-proposal cards are all-or-nothing: one "لا" cancels both transactions (T54).

## 7. Double payment via retries (A01, A02, T50)

**Failure:** A network timeout after the wallet already executed; the client retries; or the user repeats the same request.

**Handling:** Every proposal gets an idempotency key **at proposal time**. Retries send the same key; the wallet stores `key → transaction` and returns the original result (`duplicate: true`) instead of paying twice (A01/A02). A *new* confirmation mints a *new* key, so legitimate repeats still work (T50). Wallet writes are atomic (`BEGIN IMMEDIATE`), so a crash mid-write can't half-debit.

## 8. LLM misbehavior: malformed JSON, hallucinated fields, timeouts

**Failure:** GLM-5.3 occasionally returns truncated JSON, prefixes prose to JSON, or the request times out.

**Handling:** `agent/nlu.py` parses robustly (fence-stripping, outermost-brace extraction), retries up to 3 times with a bounded client timeout (60s) and SDK-level retries for 429/5xx, and **fails loudly** — the session shows an honest error and never guesses from a half-parsed response. The prompt forbids inventing amounts/names/billers; the deterministic resolver is the final arbiter of what exists.

---

**Cross-cutting guarantee:** the *only* path to money movement is `Session._execute_proposals()`, reachable solely from the `AWAITING_CONFIRMATION` state plus a rule-based "نعم". Every failure above funnels to an honest Arabic message and a wallet that stays untouched.
