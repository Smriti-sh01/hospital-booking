import requests
from flow_config import FLOW_CONFIG, BASE_URL


def call_api(slot_name: str, session: dict):
    config = FLOW_CONFIG[slot_name].get("api")

    if not config:
        return None

    endpoint = config["endpoint"]
    method = config.get("method", "GET")

    # Replace dynamic path params like {hospital_id}
    try:
        endpoint = endpoint.format(**session)
    except KeyError:
        return {"error": "Missing required parameter for endpoint"}

    url = BASE_URL + endpoint

    # Handle query params (like ?location=Delhi)
    params = {}
    if "query_params" in config:
        for key, value_from in config["query_params"].items():
            params[key] = session.get(value_from)

    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        return {"error": str(e)}