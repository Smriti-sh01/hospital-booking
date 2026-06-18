import requests

response = requests.post("http://localhost:8000/api/healthcare/chat/qa", json={
    "messageText": "hi",
    "sessionId": "test-1234"
})
print(response.json())
