from __future__ import annotations

import json
import os
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv
from state import AppointmentState, REQUIRED_SLOTS

load_dotenv()
logger = logging.getLogger(__name__)

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

HOSPITAL_KNOWLEDGE = """
You are a hospital appointment assistant for CareFirst Hospital Group.

== Hospital Information ==
CareFirst Hospital Group operates in Mumbai, Delhi, Bangalore, Hyderabad, and Chennai.
All specific information regarding available branches, departments, doctors, and their schedules will be provided dynamically during the booking process. Do NOT assume or make up any predefined branches or departments.

Working hours: Mon–Sat 8 AM – 8 PM; Emergency 24/7

Insurance: We accept all major insurance plans. Bring your card.
Parking: Free parking available at all branches.

== Booking flow ==
To book an appointment you need: city → branch → department → doctor → time slot.
"""

CLASSIFY_SYSTEM = HOSPITAL_KNOWLEDGE + """

== Your task ==
Analyse the latest user message. Return ONLY a JSON object.
Include a key only when its value is clearly stated — do NOT guess.

Keys to extract:
  intent           : "book_appointment" | "greeting" | "info_query" | "cancel" | "other"
  city             : string  (city name, exact user phrasing)
  branch           : string  (branch name)
  department       : string  (e.g. "Cardiology")
  doctor           : string  (e.g. "Dr. Sharma")
  time_slot        : string  (e.g. "Monday 10 AM")
  intent_change    : true | false
  proposed_intent  : string | null
  general_answer   : string | null   ← if intent is "info_query", put a helpful
                                        answer here using the hospital knowledge above.

Rules:
- Use EXACT user phrasing for slot values. Do not normalise.
- intent_change = true ONLY when user clearly wants a completely different service
  while an active booking is in progress.
- Return ONLY the JSON object. No markdown. No preamble.
"""

async def llm_classify_node(state: AppointmentState) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return {"step": "llm_classify"}

    last_user_msg = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )

    pending_slots = state.get("pending_slots", [])
    context_msg = f"User message: {last_user_msg}\nPending slots we are waiting for: {pending_slots}"

    try:
        print("Calling Gemini API...")
        resp = await _client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=context_msg,
            config=types.GenerateContentConfig(
                system_instruction=CLASSIFY_SYSTEM,
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        print("Gemini raw response:", resp.text)
        extracted: dict = json.loads(resp.text)
    except Exception as exc:
        print("Gemini exception occurred:", repr(exc))
        logger.warning("Gemini classify failed: %s", exc)
        return {
            "intent": "error",
            "response": {"type": "text", "answer": "I'm sorry, our AI service is currently overwhelmed (Rate Limit Exceeded). Please wait a moment and try again."},
            "step": "llm_classify"
        }

    # ✅ 1. SAFE INTENT NORMALIZATION
    intent = extracted.get("intent") or "other"
    intent = intent.lower().replace(" ", "_")

    # ✅ 2. FORCE GREETING PRIORITY (rule-based override)
    msg_lower = last_user_msg.lower().strip()
    if msg_lower in ["hi", "hello", "hey", "greetings", "hi there", "hello there"]:
        intent = "greeting"

    # ✅ 3. VALIDATE INTENT
    allowed_intents = {
        "book_appointment",
        "greeting",
        "info_query",
        "cancel",
        "other",
    }
    if intent not in allowed_intents:
        intent = "other"

    # ✅ 4. SAFE SLOT EXTRACTION
    slot_values = {
        k: v.strip()
        for k, v in extracted.items()
        if k in REQUIRED_SLOTS and isinstance(v, str) and v.strip()
    }

    # ✅ 5. MERGE WITH EXISTING SESSION SLOTS
    filled_slots = state.get("filled_slots", {}).copy()
    filled_slots.update(slot_values)

    # ✅ 6. SAFE INTENT CHANGE
    intent_change = bool(extracted.get("intent_change", False))

    # prevent random switching unless booking in progress
    if state.get("active_flow") != "booking":
        intent_change = False

    # ✅ 7. SET ACTIVE FLOW
    active_flow = state.get("active_flow")
    if intent == "book_appointment":
        active_flow = "booking"

    return {
        "intent": intent,
        "intent_change": intent_change,
        "proposed_intent": extracted.get("proposed_intent"),
        "last_extracted_slots": slot_values,
        "filled_slots": filled_slots,  # ✅ IMPORTANT
        "general_answer": extracted.get("general_answer"),
        "active_flow": active_flow,    # ✅ IMPORTANT: Persist active flow
        "step": "llm_classify",
    }
