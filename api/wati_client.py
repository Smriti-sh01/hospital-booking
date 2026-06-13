"""
api/wati_client.py
──────────────────
Sends replies back to WhatsApp users via the WATI API.

Two message types:
  • slot_options  → WATI Interactive List Message (user taps an option)
  • text / booking_confirmed  → plain Session Message
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

WATI_ENDPOINT: str = os.getenv("WATI_API_ENDPOINT", "")
WATI_TOKEN:    str = os.getenv("WATI_API_TOKEN", "")


async def send_whatsapp_reply(phone: str, response: dict[str, Any]) -> None:
    """
    Route the outbound response dict to the correct WATI API call.

    Args:
        phone:    WhatsApp phone number (digits only, with country code).
        response: The 'response' dict built by response_node.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        headers = {"Authorization": f"Bearer {WATI_TOKEN}"}

        if response.get("type") == "slot_options":
            # Send interactive list so user can tap an option
            body = {
                "phone":    phone,
                "header":   response.get("question", "Please choose"),
                "body":     response.get("question", "Please choose an option below."),
                "footer":   "Powered by Hospital Bot",
                "buttonText": "See options",
                "sections": [
                    {
                        "title": response.get("slot", "Options").replace("_", " ").title(),
                        "rows":  [
                            {"id": opt["id"], "title": opt["label"]}
                            for opt in response.get("options", [])
                        ],
                    }
                ],
            }
            url = f"{WATI_ENDPOINT}/api/v1/sendInteractiveListMessage?whatsappNumber={phone}"
            await client.post(url, json=body, headers=headers)

        else:
            # Plain text message
            message = response.get("message", "")
            url = f"{WATI_ENDPOINT}/api/v1/sendSessionMessage/{phone}"
            await client.post(url, json={"messageText": message}, headers=headers)


async def send_text(phone: str, text: str) -> None:
    """Convenience wrapper for sending a plain text message."""
    await send_whatsapp_reply(phone, {"type": "text", "message": text})