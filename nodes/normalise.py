# """
# nodes/normalise.py
# ──────────────────
# NODE 1 — normalise_input_node

# Cleans the raw incoming message and prepares it for LLM processing.
# Works for both WebChat and WhatsApp payloads — by this point the channel
# adapter has already extracted the text string and set channel_id.

# Returns partial state with 'messages' updated (last user message cleaned).
# """
# from __future__ import annotations
# import re
# from state import AppointmentState


# def normalise_input_node(state: AppointmentState) -> dict:
#     """
#     - Strip HTML tags
#     - Collapse whitespace
#     - Deduplicate consecutive identical messages (simple dedup)
#     - Ensure messages list exists
#     """
#     messages = list(state.get("messages", []))

#     if not messages:
#         return {"messages": messages, "step": "normalise_input"}

#     # Clean the last user message
#     last = messages[-1]
#     if last.get("role") == "user":
#         clean_text = _clean(last["content"])
#         messages[-1] = {**last, "content": clean_text}

#     return {
#         "messages": messages,
#         "step": "normalise_input",
#     }


# def _clean(text: str) -> str:
#     text = re.sub(r"<[^>]+>", " ", text)        # strip HTML
#     text = re.sub(r"\s+", " ", text).strip()     # collapse whitespace
#     return text

"""nodes/normalise.py"""
import re
from state import AppointmentState

def normalise_input_node(state: AppointmentState) -> dict:
    messages = list(state.get("messages", []))
    if messages and messages[-1].get("role") == "user":
        text = messages[-1]["content"]
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        messages[-1] = {**messages[-1], "content": text}
    return {"messages": messages, "step": "normalise_input"}