# Full Disclosure — Models, Tools, Data

Per the competition rules, everything used to build and run this project:

## Models

| Component | Model | Role |
|---|---|---|
| NLU / "brain" | **z-ai/glm-5.3** via NVIDIA NIM (`integrate.api.nvidia.com/v1`), OpenAI-compatible API | Extracts structured intents (action, amount, recipient, biller) from Iraqi-Arabic requests. It **only proposes** — it has no wallet credentials and no execution path. |
| Voice input (stretch) | **faster-whisper `large-v3-turbo`**, int8 on CPU | Speech-to-text for spoken Iraqi Arabic, with an Iraqi-dialect `initial_prompt`; transcript then goes through the same text pipeline (same confirmation rules). |
| Data generation | **z-ai/glm-5.3** (same endpoint) | Generated the mock wallet contents from `data_gen/wallet_schema.json` and drafted the test requests from category definitions — both then hand-edited (see `data_gen/prompts.md`). |

## AI coding assistants

This project was built **with AI assistance, openly**:

- **opencode** CLI (agent: `z-ai/glm-5.3` via NVIDIA NIM) was used for the majority of code authoring, test-set drafting, debugging, and iteration. Human (team) direction: requirements mapping, product decisions, dialect review, acceptance of results.
- All AI-generated data was hand-reviewed before use; the seed wallet and test set were edited for realism by hand.

## Tools & libraries

- **Python 3.12**, **FastAPI** + **Uvicorn** (wallet API + web backend), **SQLite** (mock wallet store), **httpx** (agent↔wallet client, idempotency keys), **python-dotenv**, **openai** SDK (GLM calls), **faster-whisper** (voice).
- Testing: custom harness (`tests/run_tests.py`) with replay/live modes; no external test framework needed for harness-level evaluation.
- Frontend: single-file HTML/CSS/JS chat UI (no framework — deliberate simplicity).

## Data

- **No real customer data of any kind.** Users, contacts, phones, billers, balances and transaction histories are **LLM-generated from a schema** (`data_gen/wallet_schema.json` → `data/seed_data.json`), hand-edited for realism.
- The main test set (`tests/testset_iraqi.json`, 55 chat cases) was **LLM-drafted from category definitions then hand-edited**, and was iterated on during development (it is the tuning set).
- The **held-out set** (`tests/testset_heldout.json`, 10 cases) was written *after* development froze and run only for reporting — see `tests/results_heldout.md`.
- Wallet data is regenerated from seed by `POST /admin/reset` before every test case, so results are reproducible.

## API key handling

The GLM endpoint key lives in `.env` (git-ignored; only `.env.example` is committed). No secrets appear in code, tests, or logs.
