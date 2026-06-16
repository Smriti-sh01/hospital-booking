"""
main.py
FastAPI entry point for chatbot backend
"""

from dotenv import load_dotenv
import re

def normalize_text(text: str) -> str:
    return re.sub(r'[^a-z0-9]', '', text.lower())
    
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
# @app.post("/api/healthcare/chat/qa")
@app.post("/api/healthcare/chat/qa")
async def chat(data: ChatRequest):

    user_message = data.messageText
    session_id = data.sessionId

    print("RECEIVED:", user_message)

    # Get session
    session = sessions.get(session_id)

    if not session:
        session = {}

    # STEP 0: Handle Greetings
    msg_lower = user_message.lower().strip()
    if msg_lower in ["hi", "hello", "hey", "greetings"]:
        from nodes.greeting import greeting_node
        greet_state = greeting_node({})
        return {
            "answer": greet_state["response"]["message"],
            "type": "text"
        }

    # STEP 0.5: Handle generic booking intent
    booking_phrases = [
        "i want to book an appointment", 
        "book appointment", 
        "book an appointment", 
        "make an appointment", 
        "appointment"
    ]
    if msg_lower in booking_phrases and "city" in session:
        return {
            "answer": "You are already inside the booking flow! Please continue by selecting the options provided.",
            "type": "text"
        }

    # STEP 1: Extract city
    mentioned_city = extract_city(user_message)
    if mentioned_city:
        if session.get("city") != mentioned_city:
            session["city"] = mentioned_city
            session.pop("branch", None)
            session.pop("branch_id", None)
            session.pop("hospital_id", None)
            session.pop("hospitals", None)
            session.pop("department", None)
            session.pop("department_id", None)
            session.pop("departments", None)
            sessions[session_id] = session

    if "city" not in session:
        sessions[session_id] = session   
        return {
            "answer": "Which city do you want to book appointment in?",
            "type": "text"
        }

    # STEP 1.5: Capture selected hospital (branch)
    if "branch" not in session and "hospitals" in session:
        norm_user = normalize_text(user_message)
        for h in session["hospitals"]:
            norm_h = normalize_text(h["name"])
            if h["name"].lower() == user_message.lower() or str(h["id"]) == str(user_message).strip() or norm_h in norm_user:
                session["branch"] = h["name"]
                session["branch_id"] = h["id"]
                sessions[session_id] = session
                break

    # STEP 2: Fetch hospitals
    if "branch" not in session:

        response = call_api("branch", {"city": session["city"]})
        hospitals = response.get("data", [])

        if not hospitals:
            from flow_config import FLOW_CONFIG
            available_cities = list(FLOW_CONFIG.get("city", {}).get("options", ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai"]))
            
            if session["city"] in available_cities:
                available_cities.remove(session["city"])
                
            options = [
                {
                    "label": c,
                    "value": c,
                    "id": c.lower()
                }
                for c in available_cities
            ]
            
            failed_city = session.pop("city", None)
            sessions[session_id] = session

            return {
                "answer": f"No hospitals found for {failed_city}. Please select from the available cities below:",
                "type": "options",
                "options": options
            }

        session["hospitals"] = hospitals
        sessions[session_id] = session

        # Try to match branch directly from the message
        norm_user = normalize_text(user_message)
        for h in hospitals:
            norm_h = normalize_text(h["name"])
            if h["name"].lower() == user_message.lower() or str(h["id"]) == str(user_message).strip() or norm_h in norm_user:
                session["branch"] = h["name"]
                session["branch_id"] = h["id"]
                sessions[session_id] = session
                break

        if "branch" not in session:
            options = [
                {
                    "label": h["name"],
                    "value": h["name"],
                    "id": str(h["id"])
                }
                for h in hospitals
            ]

            return {
                "answer": f"Please select a hospital in {session['city']}:",
                "type": "options",
                "options": options
            }

    # STEP 2.5: Capture selected department
    if "department" not in session and "departments" in session:
        norm_user = normalize_text(user_message)
        for d in session["departments"]:
            norm_d = normalize_text(d["name"])
            if d["name"].lower() == user_message.lower() or str(d["id"]) == str(user_message).strip() or norm_d in norm_user or norm_d.replace('logy', 'logist') in norm_user:
                session["department"] = d["name"]
                session["department_id"] = d["id"]
                sessions[session_id] = session
                break

    # STEP 3: Fetch departments
    if "department" not in session:
        session["hospital_id"] = session["branch_id"]
        response = call_api("department", session)
        print("API RESPONSE:", response)
        departments = response.get("data", [])

        if not departments:
            failed_branch_id = session.pop("branch_id", None)
            session.pop("branch", None)
            session.pop("hospital_id", None)
            
            if "hospitals" in session:
                session["hospitals"] = [h for h in session["hospitals"] if str(h["id"]) != str(failed_branch_id)]
                
            sessions[session_id] = session
            
            options = []
            if session.get("hospitals"):
                options = [
                    {
                        "label": h["name"],
                        "value": h["name"],
                        "id": str(h["id"])
                    }
                    for h in session["hospitals"]
                ]
            
            if options:
                return {
                    "answer": "No departments found for this hospital. Please select another hospital:",
                    "type": "options",
                    "options": options
                }
            else:
                return {
                    "answer": "No departments found for this hospital, and no other hospitals are available.",
                    "type": "text"
                }

        session["departments"] = departments
        sessions[session_id] = session

        # Try to match department directly from the message
        norm_user = normalize_text(user_message)
        for d in departments:
            norm_d = normalize_text(d["name"])
            if d["name"].lower() == user_message.lower() or str(d["id"]) == str(user_message).strip() or norm_d in norm_user or norm_d.replace('logy', 'logist') in norm_user:
                session["department"] = d["name"]
                session["department_id"] = d["id"]
                sessions[session_id] = session
                break

        if "department" not in session:
            options = [
                {
                    "label": d["name"],
                    "value": d["name"],
                    "id": str(d["id"])
                }
                for d in departments
            ]

            return {
                "answer": f"Please select a department at {session['branch']}:",
                "type": "options",
                "options": options
            }

    # STEP 3.5: Capture selected doctor
    if "doctor" not in session and "doctors" in session:
        norm_user = normalize_text(user_message)
        for doc in session["doctors"]:
            norm_doc = normalize_text(doc["name"])
            if doc["name"].lower() == user_message.lower() or str(doc["id"]) == str(user_message).strip() or norm_doc in norm_user:
                session["doctor"] = doc["name"]
                session["doctor_id"] = doc["id"]
                sessions[session_id] = session
                break

    # STEP 4: Fetch doctors
    if "doctor" not in session:
        response = call_api("doctor", session)
        doctors = response.get("data", [])

        if not doctors:
            failed_dep_id = session.pop("department_id", None)
            session.pop("department", None)
            
            if "departments" in session:
                session["departments"] = [d for d in session["departments"] if str(d["id"]) != str(failed_dep_id)]
            sessions[session_id] = session
            
            options = []
            if session.get("departments"):
                options = [
                    {
                        "label": d["name"],
                        "value": d["name"],
                        "id": str(d["id"])
                    }
                    for d in session["departments"]
                ]
            
            if options:
                return {
                    "answer": "No doctors found for this department. Please select another department:",
                    "type": "options",
                    "options": options
                }
            else:
                return {
                    "answer": "No doctors found for this department, and no other departments are available.",
                    "type": "text"
                }

        session["doctors"] = doctors
        sessions[session_id] = session

        # Try to match doctor directly from the message
        norm_user = normalize_text(user_message)
        for doc in doctors:
            norm_doc = normalize_text(doc["name"])
            norm_doc_stripped = norm_doc.replace("dr", "")
            if doc["name"].lower() == user_message.lower() or str(doc["id"]) == str(user_message).strip() or norm_doc in norm_user or (norm_doc_stripped and norm_doc_stripped in norm_user):
                session["doctor"] = doc["name"]
                session["doctor_id"] = doc["id"]
                sessions[session_id] = session
                break

        if "doctor" not in session:
            options = [
                {
                    "label": doc["name"],
                    "value": doc["name"],
                    "id": str(doc["id"])
                }
                for doc in doctors
            ]

            return {
                "answer": f"Please select a doctor for {session['department']}:",
                "type": "options",
                "options": options
            }

    return {
        "answer": "Flow working correctly ",
        "type": "text"
    }