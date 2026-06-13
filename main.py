"""
main.py
FastAPI entry point for chatbot backend
"""

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api_service import call_api

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


# In-memory session store
sessions = {}


@app.get("/health")
async def health():
    return {"status": "ok"}


# Extract city
def extract_city(message: str):
    message = message.lower()

    if "delhi" in message:
        return "Delhi"
    if "mumbai" in message:
        return "Mumbai"
    if "bangalore" in message:
        return "Bangalore"
    return None


# Chat API
@app.post("/api/healthcare/chat/qa")
@app.post("/api/healthcare/chat/qa")
async def chat(data: ChatRequest):

    user_message = data.messageText
    session_id = data.sessionId

    print("RECEIVED:", user_message)

    # Get session
    session = sessions.get(session_id)

    if not session:
        session = {}

    # STEP 1: Extract city
    if "city" not in session:
        city = extract_city(user_message)

        if city:
            session["city"] = city
            sessions[session_id] = session   # ✅ SAVE SESSION
        else:
            sessions[session_id] = session   # ✅ SAVE SESSION
            return {
                "answer": "Which city do you want to book appointment in?",
                "type": "text"
            }

    # STEP 2: Fetch hospitals
    if "branch" not in session:

        response = call_api("branch", {"city": session["city"]})
        hospitals = response.get("data", [])

        if not hospitals:
            return {
                "answer": "No hospitals found",
                "type": "text"
            }

        options = [
            {
                "label": h["name"],
                "value": h["name"],
                "id": str(h["id"])
            }
            for h in hospitals
        ]

        session["hospitals"] = hospitals
        sessions[session_id] = session   # ✅ SAVE AGAIN

        return {
            "answer": f"Please select a hospital in {session['city']}:",
            "type": "options",
            "options": options
        }

    return {
        "answer": "Flow working correctly ✅",
        "type": "text"
    }