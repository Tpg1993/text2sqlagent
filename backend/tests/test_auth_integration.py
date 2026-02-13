"""
Test script for JWT Authentication.
Tests login flow and protected endpoints.
"""
import requests
import sys
import time

# Add backend to path (parent directory of 'tests')
# Add backend to path (parent directory of 'tests')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Use port 8000 for standard instance
BASE_URL = "http://localhost:8000/api/v1"

def test_auth():
    print("=" * 60)
    print("🔐 JWT Authentication Test (Port 8002)")
    print("=" * 60)
    
    # Wait for server to start
    print("Waiting for server to be ready...")
    for i in range(10):
        try:
            requests.get("http://localhost:8002/health")
            print("Server is up!")
            break
        except:
            time.sleep(1)
    else:
        print("❌ Server failed to start on port 8001")
        return

    # 1. Login to get token
    print("\n1️⃣  Testing Login (POST /auth/login)...")
    try:
        login_data = {
            "username": "admin",
            "password": "password"  # Password doesn't matter in our mock auth
        }
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            print(f"   ✅ Login Successful!")
            print(f"   🔑 Token: {access_token[:20]}...")
        else:
            print(f"   ❌ Login Failed: {response.status_code} - {response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # 2. Test Protected Endpoint WITHOUT Token
    print("\n2️⃣  Testing Protected Endpoint WITHOUT Token...")
    try:
        chat_data = {"message": "Hello"}
        response = requests.post(f"{BASE_URL}/chat", json=chat_data)
        
        if response.status_code == 401:
            print(f"   ✅ Correctly Rejected (401 Unauthorized)")
        else:
            print(f"   ❌ Security Fail! Status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 3. Test Protected Endpoint WITH Token
    print("\n3️⃣  Testing Protected Endpoint WITH Token...")
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        chat_data = {"message": "Hello from authenticated user"}
        response = requests.post(f"{BASE_URL}/chat", json=chat_data, headers=headers)
        
        if response.status_code == 200:
            print(f"   ✅ Access Granted (200 OK)")
            # print(f"   📄 Response: {response.json().get('response')[:50]}...")
        else:
            print(f"   ❌ Request Failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ Auth Test Completed")
    print("=" * 60)

if __name__ == "__main__":
    test_auth()
