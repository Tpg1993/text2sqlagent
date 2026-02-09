import requests
import json

url = "http://localhost:8000/api/v1/chat"
payload = {
    "message": "Show me the total sales amount for each employee."
}

print(f"Testing full application with Gemini 2.5 Flash...")
print(f"URL: {url}\n")

try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ APPLICATION WORKING!")
        print(f"\nResponse:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Status {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
