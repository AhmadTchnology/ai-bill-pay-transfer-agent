"""Voice smoke test — end-to-end spoken Iraqi Arabic through the REAL pipeline:
audio upload (webm/opus, the browser mic format) -> faster-whisper STT ->
GLM-5.3 NLU -> confirmation state machine -> mock wallet -> result.

Prerequisites (already running for the demo):
  py -m uvicorn wallet_api.main:app --port 8001
  py -m uvicorn web.app:app --port 8000
  .env with GLM credentials

Fixtures are generated with edge-tts Iraqi voices if missing:
  py tests/make_voice_fixtures.py

Run:  py tests/voice_smoke.py
"""

import sys
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "voice_fixtures"
WEB = "http://127.0.0.1:8000"
WALLET = "http://127.0.0.1:8001"
START_BALANCE = 450000


def ensure_fixtures():
    if not (FIXTURES / "transfer_zainab.webm").exists():
        print("fixtures missing — generating (needs edge-tts)...")
        import make_voice_fixtures  # noqa: F401  runs the generator
        import asyncio

        asyncio.run(make_voice_fixtures.main())


def say(web: httpx.Client, sid: str, audio: str) -> dict:
    """Upload one spoken utterance to /api/voice, like the browser mic does."""
    path = FIXTURES / audio
    r = web.post(
        f"{api_voice_url(sid)}",
        files={"file": (audio, path.read_bytes(), "audio/webm")},
    )
    r.raise_for_status()
    return r.json()


def api_voice_url(sid: str) -> str:
    return f"{WEB}/api/voice?sid={sid}" if sid else f"{WEB}/api/voice"


def wallet_balance() -> int:
    return httpx.get(f"{WALLET}/users/u1", timeout=10).json()["balance_iqd"]


def main() -> int:
    ensure_fixtures()
    web = httpx.Client(timeout=300)  # transcription can take a while on CPU

    # health checks
    try:
        httpx.get(f"{WALLET}/health", timeout=5)
        web.get(f"{WEB}/", timeout=5)
    except Exception as e:
        print(f"servers not reachable: {e}")
        print("start: py -m uvicorn wallet_api.main:app --port 8001")
        print("       py -m uvicorn web.app:app --port 8000")
        return 2

    results = []

    # ---- Flow 1: spoken transfer -> card -> spoken confirm -> executed ----
    httpx.post(f"{WALLET}/admin/reset", timeout=10)
    sid = ""
    r = say(web, sid, "transfer_zainab.webm")
    sid = r["sid"]
    print(f"[1a] transcript: {r['transcript']!r}")
    ok_card = bool(r["cards"]) and r["state"] == "AWAITING_CONFIRMATION"
    results.append(("spoken transfer shows confirmation card", ok_card))

    r = say(web, sid, "confirm_yes.webm")
    print(f"[1b] transcript: {r['transcript']!r}")
    ok_exec = any(e.get("ok") for e in r["executed"])
    results.append(("spoken 'نعم' executes the transfer", ok_exec))
    bal = wallet_balance()
    results.append(
        (
            f"wallet debited exactly once (balance {bal} == {START_BALANCE - 50000})",
            bal == START_BALANCE - 50000,
        )
    )

    # ---- Flow 2: ambiguous Ahmed by voice -> must ask, never guess ----
    httpx.post(f"{WALLET}/admin/reset", timeout=10)
    r = say(web, "", "ambiguous_ahmed.webm")
    sid2 = r["sid"]
    print(f"[2] transcript: {r['transcript']!r}")
    results.append(
        (
            "spoken ambiguous 'أحمد' produces a question with choices",
            r["choices"] is not None and len(r["choices"]) >= 2,
        )
    )

    # ---- Flow 3: spoken bill request -> asks for amount ----
    r = say(web, "", "bill_electricity.webm")
    print(f"[3] transcript: {r['transcript']!r}")
    results.append(
        (
            "spoken bill without amount asks for the amount",
            any("شلون" in m for m in r["messages"]),
        )
    )

    # ---- Flow 4: spoken balance query ----
    r = say(web, "", "balance.webm")
    print(f"[4] transcript: {r['transcript']!r}")
    results.append(
        (
            "spoken 'كم رصيدي' reports the balance",
            any("رصيدك الحالي" in m for m in r["messages"]),
        )
    )

    print()
    passed = 0
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        passed += ok
    print(f"\nVOICE SMOKE: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
