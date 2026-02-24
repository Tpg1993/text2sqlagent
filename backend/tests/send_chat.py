import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

def test_api():
    # Login as admin to get the token
    print("Logging in...")
    login_res = requests.post("http://localhost:8000/api/v1/auth/login", data={"username": "admin", "password": "admin@123"})
    if login_res.status_code != 200:
        print("Login failed:", login_res.text)
        return
        
    token = login_res.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Send chat
    print("Sending chat...")
    req_body = {
        "message": "List all customers from California",
        "session_id": "test_script_session"
    }
    try:
        # Simulate EventSource connection
        print("Opening stream...")
        stream_res = requests.get(f"http://localhost:8000/api/v1/stream/{req_body['session_id']}?token={token}")
        print("Stream status:", stream_res.status_code)
        
        chat_res = requests.post("http://localhost:8000/api/v1/chat", json=req_body, headers=headers)
        print(f"Status Code: {chat_res.status_code}")
        print("Response:", chat_res.text)
    except Exception as e:
        print("Network error:", e)

if __name__ == "__main__":
    test_api()
