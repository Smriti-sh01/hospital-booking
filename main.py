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

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/healthcare/chat/qa")
async def chat(data: ChatRequest):
    user_message = data.messageText
    session_id = data.sessionId

    print("RECEIVED:", user_message)

    initial_state = {
        "channel_id": session_id,
        "messages": [{"role": "user", "content": user_message}]
    }

    try:
        final_state = await compiled_graph.ainvoke(initial_state)
    except Exception as e:
        print("Graph execution error:", str(e))
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