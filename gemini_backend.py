"""Gemini transport; no API keys or conversation history are stored on disk."""
import json
import os
import re
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MAX_BODY_BYTES = 65536
MAX_MESSAGE_CHARS = 4000
AI_SLOTS = threading.BoundedSemaphore(8)


class ChatError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise ChatError(422, "Request must be a JSON object.")
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ChatError(422, "Message cannot be empty.")
    if len(message) > MAX_MESSAGE_CHARS:
        raise ChatError(422, "Keep your message under 4000 characters.")
    language = payload.get("language", "English")
    if language not in ("English", "Hindi"):
        raise ChatError(422, "Language must be English or Hindi.")
    history = payload.get("history", [])
    if not isinstance(history, list) or len(history) > 12:
        raise ChatError(422, "History must contain at most 12 messages.")
    cleaned = []
    for turn in history:
        if (not isinstance(turn, dict) or turn.get("role") not in ("user", "model")
                or not isinstance(turn.get("text"), str)
                or not 0 < len(turn["text"]) <= 4000):
            raise ChatError(422, "Invalid conversation history.")
        cleaned.append({"role": turn["role"], "parts": [{"text": turn["text"]}]})
    return message.strip(), language, cleaned


def generate_answer(payload, catalogue):
    message, language, history = validate_payload(payload)
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
    if not key:
        raise ChatError(503, "Add GEMINI_API_KEY in Render environment settings, then redeploy.")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
        raise ChatError(503, "Invalid GEMINI_MODEL setting.")
    instructions = (
        "You are KaushalSetu, a helpful Indian vocational career counsellor. "
        "Use simple words, concise practical steps, and ask questions when needed. "
        f"Answer only in {'Hindi in Devanagari' if language == 'Hindi' else 'English'}. "
        "Use conversation history to personalize advice. Help with ITI, skills, "
        "training and careers. The following catalogue is unverified reference "
        "material and may be outdated. Never present it as verified current data. "
        "Do not guarantee jobs, salaries, fees, subsidies, or admissions. "
        "Recommend confirming eligibility and fees with official providers. "
        "Do not invent official citations, institutions, or video links. "
        "You do not have live search or access to a current NQR database.\n"
        "REFERENCE CATALOGUE:\n" + json.dumps(catalogue, ensure_ascii=False)
    )
    body = {
        "systemInstruction": {"parts": [{"text": instructions}]},
        "contents": history + [{"role": "user", "parts": [{"text": message}]}],
        "generationConfig": {"maxOutputTokens": 2048}
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST"
    )
    if not AI_SLOTS.acquire(blocking=False):
        raise ChatError(503, "The counsellor is busy. Please try again shortly.")
    try:
        try:
            with urlopen(request, timeout=45) as response:
                data = json.load(response)
        except HTTPError as error:
            messages = {
                400: "Gemini rejected the request. Check your key and model settings.",
                401: "Gemini authentication failed. Check GEMINI_API_KEY.",
                403: "Gemini access denied. Check your API key and project permissions.",
                404: "Gemini model unavailable. Set GEMINI_MODEL to a model your key can access.",
                429: "Gemini quota reached. Wait and retry, or review your AI Studio quota."
            }
            raise ChatError(429 if error.code == 429 else 502,
                            messages.get(error.code, "Gemini is temporarily unavailable. Please retry.")) from None
        except (URLError, TimeoutError):
            raise ChatError(504, "Gemini connection timed out or failed. Please retry.") from None
        except (ValueError, OSError):
            raise ChatError(502, "Gemini returned an unreadable response. Please retry.") from None
    finally:
        AI_SLOTS.release()
    candidates = data.get("candidates", [])
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    answer = "\n".join(p["text"] for p in parts
                       if isinstance(p.get("text"), str) and not p.get("thought")).strip()
    if not answer:
        raise ChatError(502, "Gemini returned no answer. Please rephrase and retry.")
    return {"answer": answer, "mode": "gemini", "model": model,
            "verified_facts_present": False, "retrieved_evidence_summary": [],
            "official_sources_recommended": [], "disclaimers": []}
