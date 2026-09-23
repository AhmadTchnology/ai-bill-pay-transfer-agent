"""Voice input (stretch goal): spoken Iraqi Arabic → text → same agent pipeline.

Uses faster-whisper with the large-v3-turbo model (int8 on CPU ≈ 2 GB RAM).
The Iraqi-dialect `initial_prompt` measurably improves dialect transcription:
it biases the decoder toward colloquial vocabulary and spelling.

The transcribed text goes through EXACTLY the same pipeline as typed input —
including the confirmation state machine. Voice can never skip the "نعم".
"""

import os
import tempfile
from pathlib import Path

MODEL_NAME = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
IRAQI_PROMPT = "لهجة عراقية: حول خمسين الف لأحمد، دفع فاتورة الكهرباء، شحن رصيد آسياسيل، اكيد، أيوة"
# Short utterances ("نعم", "كم رصيدي") get misheard without vocabulary bias —
# hotwords steer the decoder toward dialect-critical terms.
HOTWORDS = "نعم أيوة اكيد زين لا إلغاء رصيدي كم حول ابعت دفع فاتورة كهرباء ماء انترنت موبايل شحن رصيد"

_model = None


def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str | Path, language: str = "ar") -> dict:
    """Transcribe an audio file. Returns {text, language, avg_logprob}."""
    model = get_model()
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        initial_prompt=IRAQI_PROMPT,
        hotwords=HOTWORDS,
        beam_size=5,
        vad_filter=True,
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    return {
        "text": text,
        "language": info.language,
        "avg_logprob": getattr(info, "avg_logprob", None),
    }


def transcribe_fileobj(fileobj) -> dict:
    """Persist an uploaded audio blob to a temp file and transcribe it."""
    suffix = ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(fileobj.read())
        tmp_path = tmp.name
    try:
        return transcribe(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
