"""
main.py
FastAPI entry point for chatbot backend
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import compiled_graph

load_dotenv()
app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema
class ChatRequest(BaseModel):
    messageText: str
    sessionId: str
    # Optional: sent when the user picks a structured option button
    slot: str | None = None
    selectedOptionLabel: str | None = None
    selectedOptionId: str | None = None

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/healthcare/chat/qa")
async def chat(data: ChatRequest):
    user_message = data.messageText
    session_id = data.sessionId

    print("RECEIVED:", user_message)

    # Map slot names to their resolved ID field names used in API calls
    SLOT_ID_MAP = {
        "branch": "hospital_id",
        "department": "department_id",
        "doctor": "doctor_id",
        "date": "date",
        "time_slot": "slot_id",
    }

    # If the frontend tells us exactly which slot was answered (structured option pick),
    # pre-load it so the LLM doesn't need to infer from a raw numeric ID.
    pre_filled: dict = {}
    if data.slot and data.selectedOptionLabel:
        resolved_ids = {}
        slot_id_key = SLOT_ID_MAP.get(data.slot)
        if slot_id_key and data.selectedOptionId:
            resolved_ids[slot_id_key] = data.selectedOptionId

        pre_filled = {
            "filled_slots": {data.slot: data.selectedOptionLabel},
            "last_extracted_slots": {data.slot: data.selectedOptionLabel},
            "active_flow": "booking",
            "resolved_ids": resolved_ids,
            "is_option_selection": True,
        }

    initial_state = {
        "channel_id": session_id,
        "messages": [{"role": "user", "content": user_message or data.selectedOptionLabel or ""}],
        **pre_filled,
    }

    try:
        final_state = await compiled_graph.ainvoke(initial_state)
    except Exception as e:
        import traceback
        print("Graph execution error:", str(e))
        traceback.print_exc()
        return {
            "answer": "We are facing technical issues. Please try again later.",
            "type": "text"
        }

    response_dict = final_state.get("response", {
        "answer": "Flow working correctly",
        "type": "text"
    })

    if "message" in response_dict and "answer" not in response_dict:
        response_dict["answer"] = response_dict.pop("message")

    return response_dict