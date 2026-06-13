"""
api/hms_client.py
─────────────────
Thin async wrappers around the Hospital Management System REST API.

Dependency chain (each call needs the ID from the one above it):
    hospitals(city)
        └─ departments(hospital_id)
               └─ doctors(department_id)
                      └─ time_slots(doctor_id)
                             └─ confirm_booking(hospital_id, department_id,
                                               doctor_id, slot_id)

All wrappers use a shared httpx.AsyncClient (connection pool).
"""
from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

HMS_BASE_URL: str = os.getenv("HMS_BASE_URL", "https://hms.example.com/api/v1")
HMS_API_KEY:  str = os.getenv("HMS_API_KEY", "")

# ── Shared client (created once, reused) ──────────────────────────────────
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=HMS_BASE_URL,
            headers={"Authorization": f"Bearer {HMS_API_KEY}"},
            timeout=10.0,
        )
    return _client


# ── API wrappers ──────────────────────────────────────────────────────────

async def fetch_hospitals(city: str) -> list[dict[str, Any]]:
    """
    GET /hospitals?city=<city>
    Expected response shape:
        {"hospitals": [{"id": "H1", "name": "City General"}, ...]}
    """
    resp = await _get_client().get("/hospitals", params={"city": city})
    resp.raise_for_status()
    return resp.json().get("hospitals", [])


async def fetch_departments(hospital_id: str) -> list[dict[str, Any]]:
    """
    GET /departments?hospital_id=<id>
    Expected response shape:
        {"departments": [{"id": "D1", "name": "Cardiology"}, ...]}
    """
    resp = await _get_client().get("/departments", params={"hospital_id": hospital_id})
    resp.raise_for_status()
    return resp.json().get("departments", [])


async def fetch_doctors(department_id: str) -> list[dict[str, Any]]:
    """
    GET /doctors?department_id=<id>
    Expected response shape:
        {"doctors": [{"id": "DR1", "name": "Dr. Sharma", "speciality": "..."}, ...]}
    """
    resp = await _get_client().get("/doctors", params={"department_id": department_id})
    resp.raise_for_status()
    return resp.json().get("doctors", [])


async def fetch_time_slots(doctor_id: str) -> list[dict[str, Any]]:
    """
    GET /slots?doctor_id=<id>
    Expected response shape:
        {"slots": [{"id": "S1", "label": "Mon 10:00 AM", "available": true}, ...]}
    Only returns available slots.
    """
    resp = await _get_client().get("/slots", params={"doctor_id": doctor_id})
    resp.raise_for_status()
    all_slots = resp.json().get("slots", [])
    return [s for s in all_slots if s.get("available", True)]


async def confirm_booking(
    hospital_id: str,
    department_id: str,
    doctor_id: str,
    slot_id: str,
    patient_channel_id: str,
) -> dict[str, Any]:
    """
    POST /appointments
    Expected response shape:
        {"booking_ref": "APT-20240601-0042", "status": "confirmed", ...}
    """
    payload = {
        "hospital_id":         hospital_id,
        "department_id":       department_id,
        "doctor_id":           doctor_id,
        "slot_id":             slot_id,
        "patient_channel_id":  patient_channel_id,
    }
    resp = await _get_client().post("/appointments", json=payload)
    resp.raise_for_status()
    return resp.json()


# ── ID resolver ───────────────────────────────────────────────────────────

def resolve_id(items: list[dict[str, Any]], name_or_label: str) -> str:
    """
    Find the 'id' field in a list of API items whose 'name' or 'label'
    best matches *name_or_label* (case-insensitive, partial match).

    Falls back to the first item if nothing matches.
    Raises ValueError if the list is empty.
    """
    if not items:
        raise ValueError(f"Cannot resolve id: item list is empty (looking for '{name_or_label}')")

    needle = name_or_label.lower().strip()
    for item in items:
        candidate = (item.get("name") or item.get("label") or "").lower()
        if needle in candidate or candidate in needle:
            return item["id"]

    # Fallback: first item
    return items[0]["id"]