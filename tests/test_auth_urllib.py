
import urllib.request
import urllib.parse
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    print("Test Login...")
    data = urllib.parse.urlencode({"username": "admin", "password": "password"}).encode()
    req = urllib.request.Request(f"{BASE_URL}/auth/login", data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode()
            token = json.loads(res_body)["access_token"]
            print("Login Success for token: " + token[:10] + "...")
    except Exception as e:
        print(f"Login Failed: {e}")
        return

    print("Test Protected (No Token)...")
    req = urllib.request.Request(f"{BASE_URL}/chat", data=json.dumps({"message": "hi"}).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req)
        print("FAIL: Should be 401")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("PASS: 401 Unauthorized")
        else:
            print(f"FAIL: {e.code}")
    except Exception as e:
        print(f"FAIL: {e}")

    print("Test Protected (With Token)...")
    req = urllib.request.Request(f"{BASE_URL}/chat", data=json.dumps({"message": "hi"}).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        # We expect a long timeout or streaming response, so just checking connection/status is enough
        # But urllib might hang if it's streaming. 
        # API returns regular JSON unless it's the stream endpoint.
        # /chat is POST and returns ChatResponse (JSON).
        with urllib.request.urlopen(req) as response:
            print(f"PASS: {response.status}")
            print(response.read().decode())
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == "__main__":
    run_test()
