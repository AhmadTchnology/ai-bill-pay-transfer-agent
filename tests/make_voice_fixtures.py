"""Generates Iraqi-Arabic test audio with edge-tts (ar-IQ voices) for the voice
smoke test. Run:  py tests/make_voice_fixtures.py"""

import asyncio
from pathlib import Path

import edge_tts

OUT = Path(__file__).parent / "voice_fixtures"
OUT.mkdir(exist_ok=True)

# Iraqi-dialect phrases covering the main flows
PHRASES = {
    "transfer_zainab": ("حول خمسين الف لزينب", "ar-IQ-BasselNeural"),
    "ambiguous_ahmed": ("حول خمسين الف لأحمد", "ar-IQ-BasselNeural"),
    "bill_electricity": ("دفع فاتورة الكهرباء", "ar-IQ-BasselNeural"),
    "confirm_yes": ("نعم", "ar-IQ-BasselNeural"),
    "cancel_no": ("لا، إلغاء", "ar-IQ-BasselNeural"),
    "balance": ("كم رصيدي؟", "ar-IQ-BasselNeural"),
}


def to_webm_opus(src: Path, dst: Path):
    """Convert to webm/opus — the exact container/codec the browser
    MediaRecorder uploads, so we test the real mic path."""
    import av

    inp = av.open(str(src))
    out = av.open(str(dst), "w")
    stream = out.add_stream("libopus", rate=48000)
    for frame in inp.decode(audio=0):
        for p in stream.encode(frame):
            out.mux(p)
    for p in stream.encode(None):
        out.mux(p)
    out.close()


async def main():
    for stem, (text, voice) in PHRASES.items():
        mp3 = OUT / f"{stem}.mp3"
        await edge_tts.Communicate(text, voice).save(str(mp3))
        to_webm_opus(mp3, OUT / f"{stem}.webm")
        print(f"generated: {stem}.mp3 + {stem}.webm  <-  {text}")


if __name__ == "__main__":
    asyncio.run(main())
