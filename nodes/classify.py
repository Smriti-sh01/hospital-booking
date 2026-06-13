async def llm_classify_node(state: AppointmentState) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return {"step": "llm_classify"}

    last_user_msg = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )

    try:
        resp = await _client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": last_user_msg},
            ],
        )
        extracted: dict = json.loads(resp.choices[0].message.content)
    except Exception as exc:
        logger.warning("OpenAI classify failed: %s", exc)
        extracted = {}

    # ✅ 1. SAFE INTENT NORMALIZATION
    intent = extracted.get("intent") or "other"
    intent = intent.lower().replace(" ", "_")

    # ✅ 2. FORCE GREETING PRIORITY (rule-based override)
    msg_lower = last_user_msg.lower()
    if any(g in msg_lower for g in ["hi", "hello", "hey"]):
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

    return {
        "intent": intent,
        "intent_change": intent_change,
        "proposed_intent": extracted.get("proposed_intent"),
        "last_extracted_slots": slot_values,
        "filled_slots": filled_slots,  # ✅ IMPORTANT
        "general_answer": extracted.get("general_answer"),
        "step": "llm_classify",
    }

# """
# nodes/classify.py
# ─────────────────
# NODE — llm_classify_node

# ★ MIGRATED FROM GROQ → OPENAI (gpt-4o-mini)

# Two jobs:
# 1. Extract intent + slot values from the latest user message (structured JSON).
# 2. Detect intent_change if the user wants a different service mid-flow.

# The LLM ONLY extracts data here. Flow routing is 100% done by router.py
# (pure Python — no LLM involved in routing decisions).

# HOSPITAL KNOWLEDGE BASE is fed via the system prompt so the LLM can
# answer general hospital questions ("what is cardiology?", "what are your
# hours?") in addition to extracting booking slots.
# """
# from __future__ import annotations

# import json
# import os
# import logging

# from openai import AsyncOpenAI
# from dotenv import load_dotenv

# from state import AppointmentState, REQUIRED_SLOTS

# load_dotenv()
# logger = logging.getLogger(__name__)

# _client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# # ── Hospital knowledge fed to the LLM ────────────────────────────────────
# # Edit this to match your hospital's real data.
# HOSPITAL_KNOWLEDGE = """
# You are a hospital appointment assistant for CareFirst Hospital Group.

# == Hospital Information ==
# CareFirst Hospital Group operates in Mumbai, Delhi, Bangalore, Hyderabad, and Chennai.

# Branches:
# - Mumbai : Hiranandani Branch, Kokilaben Branch
# - Delhi   : Saket Branch, Dwarka Branch
# - Bangalore: Whitefield Branch, Jayanagar Branch

# Departments available: Cardiology, Orthopedics, Neurology, Dermatology,
# Gynecology, Pediatrics, General Medicine, ENT, Ophthalmology

# Working hours: Mon–Sat 8 AM – 8 PM; Emergency 24/7

# Insurance: We accept all major insurance plans. Bring your card.
# Parking: Free parking available at all branches.

# == Booking flow ==
# To book an appointment you need: city → branch → department → doctor → time slot.
# """

# # ── Classification system prompt ─────────────────────────────────────────
# CLASSIFY_SYSTEM = HOSPITAL_KNOWLEDGE + """

# == Your task ==
# Analyse the latest user message. Return ONLY a JSON object.
# Include a key only when its value is clearly stated — do NOT guess.

# Keys to extract:
#   intent           : "book_appointment" | "greeting" | "info_query" | "cancel" | "other"
#   city             : string  (city name, exact user phrasing)
#   branch           : string  (branch name)
#   department       : string  (e.g. "Cardiology")
#   doctor           : string  (e.g. "Dr. Sharma")
#   time_slot        : string  (e.g. "Monday 10 AM")
#   intent_change    : true | false
#   proposed_intent  : string | null
#   general_answer   : string | null   ← if intent is "info_query", put a helpful
#                                         answer here using the hospital knowledge above.

# Rules:
# - Use EXACT user phrasing for slot values. Do not normalise.
# - intent_change = true ONLY when user clearly wants a completely different service
#   while an active booking is in progress.
# - Return ONLY the JSON object. No markdown. No preamble.
# """


# async def llm_classify_node(state: AppointmentState) -> dict:
#     messages = state.get("messages", [])
#     if not messages:
#         return {"step": "llm_classify"}

#     last_user_msg = next(
#         (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
#     )

#     try:
#         resp = await _client.chat.completions.create(
#             model="gpt-4o-mini",            # cheap + fast; swap to gpt-4o for better accuracy
#             temperature=0,
#             response_format={"type": "json_object"},
#             messages=[
#                 {"role": "system", "content": CLASSIFY_SYSTEM},
#                 {"role": "user",   "content": last_user_msg},
#             ],
#         )
#         extracted: dict = json.loads(resp.choices[0].message.content)
#     except Exception as exc:
#         logger.warning("OpenAI classify failed: %s", exc)
#         extracted = {}

#     # Pull only valid slot keys
#     slot_values = {
#         k: v for k, v in extracted.items()
#         if k in REQUIRED_SLOTS and isinstance(v, str) and v.strip()
#     }

#     return {
#         "intent":               extracted.get("intent"),
#         "intent_change":        bool(extracted.get("intent_change", False)),
#         "proposed_intent":      extracted.get("proposed_intent"),
#         "last_extracted_slots": slot_values,
#         "general_answer":       extracted.get("general_answer"),  # used by response_node
#         "step":                 "llm_classify",
#     }