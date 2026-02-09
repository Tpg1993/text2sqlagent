import requests
import json
import time

url = "http://localhost:8000/api/v1/chat"
payload = {
    "message": "Show me the total sales amount for each employee."
}

print(f"Testing API endpoint: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

start_time = time.time()
try:
    response = requests.post(url, json=payload, timeout=120)
    elapsed = time.time() - start_time
    print(f"Time taken: {elapsed:.2f}s")
    print(f"Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS!")
        print(f"Response: {json.dumps(data, indent=2)}\n")
    else:
        print(f"❌ FAILED - Status {response.status_code}")
        print(f"Response Text:\n{response.text}\n")
        
except Exception as e:
    print(f"❌ ERROR: {e}\n")
