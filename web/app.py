"""Web app: chat UI backend. One Session per browser (cookie-based).

The UI buttons for confirm/cancel send the literal words "نعم" / "لا" through
the same text pipeline — there is exactly ONE path to execution: the state
machine's rule-based confirmation check.
"""

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.executor import WalletClient
from agent.session import Session
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Bill Pay & Transfer Agent")
wallet = WalletClient(os.environ.get("WALLET_URL", "http://127.0.0.1:8001"))
USER_ID = os.environ.get("WALLET_USER_ID", "u1")
sessions: dict[str, Session] = {}

STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class ChatIn(BaseModel):
    text: str


def get_session(sid: str) -> Session:
    if sid not in sessions:
        sessions[sid] = Session(USER_ID, wallet, session_id=sid)
    return sessions[sid]


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/me")
def me():
    user = wallet.get_user(USER_ID)
    if not user:
        raise HTTPException(500, "wallet not reachable")
    txns = wallet.get_transactions(USER_ID, 5)
    billers = wallet.search_billers(USER_ID)
    return {"user": user, "transactions": txns, "billers": billers}


@app.post("/api/chat")
def chat(body: ChatIn, sid: str = ""):
    if not sid:
        sid = uuid.uuid4().hex[:12]
    s = get_session(sid)
    reply = s.handle(body.text)
    return {
        "sid": sid,
        "state": s.state,
        "messages": reply.messages,
        "cards": reply.cards,
        "choices": reply.choices,
        "executed": reply.executed,
    }


@app.post("/api/reset")
def reset(sid: str = ""):
    """New conversation (state machine), and reload wallet seed data."""
    if sid in sessions:
        del sessions[sid]
    try:
        import httpx

        httpx.post(f"{wallet.base}/admin/reset", timeout=5)
    except Exception:
        pass
    return {"ok": True}


@app.post("/api/voice")
async def voice(sid: str = "", file: UploadFile = ...):
    """Voice input (stretch): transcribe spoken Iraqi Arabic with faster-whisper,
    then push the transcript through EXACTLY the same pipeline as typed text —
    including the confirmation state machine. Voice can never skip the 'نعم'."""
    try:
        from voice.stt import transcribe_fileobj
    except ImportError:
        raise HTTPException(
            503, "voice support not installed: pip install faster-whisper"
        )
    try:
        result = transcribe_fileobj(file.file)
    except Exception as e:
        raise HTTPException(500, f"transcription failed: {e}")
    text = (result.get("text") or "").strip()
    if not text:
        return {
            "sid": sid,
            "transcript": "",
            "messages": ["ما سمعت شي. جرب مرة ثانية."],
            "cards": [],
            "choices": None,
            "executed": [],
        }
    s = get_session(sid or uuid.uuid4().hex[:12])
    reply = s.handle(text)
    return {
        "sid": s.session_id,
        "state": s.state,
        "transcript": text,
        "messages": reply.messages,
        "cards": reply.cards,
        "choices": reply.choices,
        "executed": reply.executed,
    }
