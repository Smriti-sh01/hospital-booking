BASE_URL = "https://demo.hms.kadellabs.com"

FLOW_CONFIG: dict[str, dict] = {
    "city": {
        "question": "Which city are you looking for a hospital in?",
        "api": None,
        "options": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai"],
    },

    "branch": {
        "question": "Which hospital branch would you prefer?",
        "api": {
            "endpoint": "/hospitals",
            "method": "GET",
            "query_params": {
                "location": "city"   
            }
        }
    },

    "department": {
        "question": "Which department do you need?",
        "api": {
            "endpoint": "/hospitals/{hospital_id}/departments",
            "method": "GET"
        }
    },

    "doctor": {
        "question": "Which doctor would you like to see?",
        "api": {
            "endpoint": "/departments/{department_id}/doctors",
            "method": "GET"
        }
    },

    "time_slot": {
        "question": "Which time slot works for you?",
        "api": {
            "endpoint": "/doctors/{doctor_id}/slots",
            "method": "GET"
        }
    },
}