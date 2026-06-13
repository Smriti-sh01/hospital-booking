"""
nodes/greeting.py
─────────────────
NODE — greeting_node

Emits a welcome message listing available services.
Runs when the router detects intent == "greeting".
"""
from __future__ import annotations
from state import AppointmentState


def greeting_node(state: AppointmentState) -> dict:
    message = (
        "👋 Hello! Welcome to our Hospital Booking Assistant.\n\n"
        "I can help you with:\n"
        "  • Book a doctor appointment\n"
        "  • Choose a hospital branch\n"
        "  • Select department and doctor\n"
        "  • Pick an available time slot\n\n"
        "Just tell me what you need — for example:\n"
        "  \"I want to book an appointment in Delhi\""
    )
    return {
        "response": {"type": "text", "message": message},
        "step":     "greeting_node",
    }