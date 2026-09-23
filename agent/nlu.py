"""NLU layer: GLM-5.3 turns Iraqi Arabic requests into structured intents.

Security model: the LLM only *proposes* — it returns JSON. It has no access to
the wallet. All money movement happens in the deterministic executor after an
explicit user confirmation. A hallucinated intent can never move money by
itself because execution requires a rule-based "yes" from the user.
"""

import json
import os
import re

from openai import OpenAI

SYSTEM_PROMPT = """You are the intent-extraction engine of an Iraqi Arabic bill-pay & money-transfer agent.
The user speaks Iraqi dialect (or MSA). Extract intent(s) and return ONLY valid JSON.

Return schema:
{
  "intents": [
    {
      "action": "transfer | bill_pay | balance_check | history | unknown",
      "amount": integer IQD or null,
      "recipient": contact name (string or null) for transfers,
      "biller": biller name/category (string or null) for bill payments,
      "note": optional short note or null
    }
  ]
}

Rules:
- Convert spoken amounts to digits: "خمسين الف" -> 50000, "خمسة وعشرين ألف" -> 25000, "مئة الف" -> 200000. Currency is always IQD. Example: "مية الف" -> 100000, "مئتين الف" -> 200000.
- If the message contains TWO requests (e.g. pay electricity AND send 5000 to Ahmed), return TWO intents.
- For bill payments, set "biller" to the user's LITERAL words (e.g. "الكهرباء", "المي", "انترنت", "آسياسيل", "زين", "كورك", "اورنج"). Map obvious synonyms only (المي -> ماء, شحن رصيد + operator -> operator). NEVER invent or substitute a different biller than what the user actually said — if the user names something unknown (e.g. "النجرة", "شركة الخيال"), pass those words through unchanged and let the system handle it.
- "شحن رصيد" (mobile topup) is bill_pay with the operator in "biller".
- If the amount is missing, use null. Do NOT invent amounts.
- If the recipient name is missing, use null. Do NOT invent names.
- "كم رصيدي" / "شو رصيد" -> balance_check. "اخر حركات" / "تاريخ الحساب" -> history.
- If the message is unclear, malformed, or not money-related, return one intent with action "unknown".
- Never add fields. Never wrap in markdown fences. Return ONLY the JSON object."""


def _client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("GLM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.environ.get("GLM_API_KEY", ""),
        timeout=60.0,  # GLM-5.3 is a reasoning model — allow generous latency,
        max_retries=2,  # the SDK already retries 429/5xx with backoff
    )


def _parse_json(raw: str) -> dict:
    """Robust JSON extraction: strips fences, handles leading prose/reasoning."""
    raw = raw.strip()
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass
    # model may prefix prose or reasoning text — grab the outermost JSON object
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        return json.loads(raw[start : end + 1])
    raise ValueError("no JSON object found in model output")


def extract_intents(text: str, history: list | None = None) -> dict:
    """Call GLM-5.3 and return the parsed intent dict.

    LLMs occasionally emit malformed JSON (truncation, stray prose). We retry a
    bounded number of times and only fail loudly after that — a money agent
    must never guess from a half-parsed response."""
    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        raise RuntimeError("GLM_API_KEY not set (see .env.example)")
    client = _client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": text})
    last_err = None
    for attempt in range(3):
        resp = client.chat.completions.create(
            model=os.environ.get("GLM_MODEL", "z-ai/glm-5.3"),
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content or ""
        try:
            parsed = _parse_json(raw)
            if "intents" in parsed and isinstance(parsed["intents"], list):
                return parsed
            last_err = ValueError("missing 'intents' list")
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
    raise RuntimeError(f"model returned invalid JSON after 3 attempts: {last_err}")
