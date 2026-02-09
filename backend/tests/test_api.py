import requests
import json

# Test the chat endpoint
url = "http://localhost:8000/api/v1/chat"
payload = {
    "message": "Show me the total sales amount for each employee."
}

print("Sending request to:", url)
print("Payload:", json.dumps(payload, indent=2))

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"\nRaw Response Text:")
    print(response.text)
    
    if response.status_code == 200:
        print(f"\nParsed JSON:")
        print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"\nError: {e}")
    if 'response' in locals():
        print(f"Response text: {response.text}")
