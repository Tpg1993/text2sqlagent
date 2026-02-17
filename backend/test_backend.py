import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test():
    try:
        # 1. Login
        print("Logging in...")
        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "admin@123"})
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
        
        token = resp.json()["access_token"]
        print(f"Got token: {token[:10]}...")
        
        # 2. Chat
        print("Sending chat request...")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {"message": "DEBUG_PYTHON_TEST", "session_id": "py_test"}
        
        resp = requests.post(f"{BASE_URL}/chat", json=data, headers=headers)
        
        print(f"Chat Status: {resp.status_code}")
        print(f"Chat Headers: {dict(resp.headers)}")
        print(f"Chat Response: {resp.text}")
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {e.response.text if e.response else 'No response'}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
