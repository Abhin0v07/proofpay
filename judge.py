import os
import json
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
PRIMARY = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
MODELS = []
for m in [PRIMARY, "gemini-3.7-flash", "gemini-3.8-flash", "gemini-3.6-flash"]:
    if m not in MODELS:
        MODELS.append(m)

PROMPT = """You are a neutral referee for a freelance escrow.
A buyer wrote a brief. A seller submitted a delivery.
Judge whether the delivery fulfils the brief.

Steps:
1. Break the brief into 2 to 5 concrete checklist items.
2. For each item decide pass or fail, with a one-sentence reason.
3. Approve ONLY if every key item passes. Be strict but fair.

Reply with JSON only, in exactly this shape:
{"approved": true or false,
 "items": [{"item": "...", "pass": true or false, "reason": "..."}],
 "summary": "one or two sentences explaining the decision"}

BRIEF:
%s

DELIVERY:
%s
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in model reply: {text[:200]}")
    return json.loads(text[start : end + 1])


def _call(model: str, brief: str, delivery: str, timeout: float) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [{"text": PROMPT % (brief, delivery)}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    r = httpx.post(url, json=body, headers={"x-goog-api-key": API_KEY}, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"Gemini {r.status_code}")
    data = r.json()
    parts = data["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    result = _extract_json(text)
    result["approved"] = bool(result.get("approved", False))
    result.setdefault("items", [])
    result.setdefault("summary", "")
    result["model"] = model
    return result


def _fallback(brief: str, delivery: str) -> dict:
    """Simple keyword referee. Only used if ALLOW_FALLBACK=1 and Gemini is down."""
    words = {w.strip(".,!?").lower() for w in brief.split() if len(w.strip(".,!?")) > 3}
    low = delivery.lower()
    items = []
    for w in sorted(words):
        ok = w in low
        items.append({
            "item": f"Delivery relates to '{w}'",
            "pass": ok,
            "reason": "Mentioned in the delivery." if ok else "Not mentioned in the delivery.",
        })
    passed = sum(1 for i in items if i["pass"])
    approved = len(delivery.strip()) > 30 and bool(items) and passed >= max(1, len(items) * 0.5)
    return {
        "approved": approved,
        "items": items,
        "summary": "Gemini was unavailable, so a simple keyword check was used instead.",
        "model": "fallback-keyword-check (Gemini unavailable)",
    }


def judge(brief: str, delivery: str) -> dict:
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing from .env")

    deadline = time.time() + 90
    errors = []
    attempt = 0
    while time.time() < deadline - 5:
        model = MODELS[attempt % len(MODELS)]
        attempt += 1
        try:
            return _call(model, brief, delivery, min(25, deadline - time.time()))
        except Exception as e:
            msg = f"{model}: {type(e).__name__} {e}"
            print("JUDGE RETRY ->", msg)
            errors.append(msg)
            time.sleep(1.5)

    if os.getenv("ALLOW_FALLBACK") == "1":
        return _fallback(brief, delivery)
    raise RuntimeError("Gemini is busy. Last errors: " + " | ".join(errors[-3:]))