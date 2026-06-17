
import logging
from state import AppointmentState, REQUIRED_SLOTS
from api_service import call_api

logger = logging.getLogger(__name__)

def _resolve_id(items: list, name: str):
    if not items or not name: return None
    for i in items:
        if i.get("name", "").lower() == name.lower():
            return i.get("id")
    return None

async def api_chain_node(state: AppointmentState) -> dict:
    extracted = state.get("last_extracted_slots", {})
    filled = {**state.get("filled_slots", {}), **extracted}
    pending = [s for s in REQUIRED_SLOTS if s not in filled]
    cache = dict(state.get("api_context", {}))

    if not pending:
        return {}

    first = pending[0]

    # Resolve IDs from previous steps so call_api has them
    session_params = dict(filled)
    if "branch" in filled and "branch" in cache:
        session_params["hospital_id"] = _resolve_id(cache["branch"], filled["branch"])
    if "department" in filled and "department" in cache:
        session_params["department_id"] = _resolve_id(cache["department"], filled["department"])
    if "doctor" in filled and "doctor" in cache:
        session_params["doctor_id"] = _resolve_id(cache["doctor"], filled["doctor"])

    if first not in cache:
        try:
            resp = call_api(first, session_params)
            cache[first] = resp.get("data", []) if isinstance(resp, dict) else []
        except Exception as e:
            logger.error("api_chain_node error: %s", e)
            cache[first] = []

    return {
        "api_context": cache,
        "step": "api_chain_node"
    }
    