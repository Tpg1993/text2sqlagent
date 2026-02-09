import requests
import json

url = "http://localhost:8000/api/v1/chat"
payload = {
    "message": "Show me the total sales amount for each employee."
}

print(f"Testing: {payload['message']}\n")

try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS!\n")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Failed")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error: {e}")
