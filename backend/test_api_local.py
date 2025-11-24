import requests
import json
import time

def test_api():
    url = "http://127.0.0.1:8000/recommend"
    payload = {
        "query": "Java developer with collaboration skills",
        "top_k": 5
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        print("\nResponse received!")
        print(json.dumps(data, indent=2))
        
        if len(data["results"]) > 0:
            print("\n✅ API Test Passed: Results returned.")
        else:
            print("\n❌ API Test Failed: No results returned.")
            
    except Exception as e:
        print(f"\n❌ API Test Failed: {e}")

if __name__ == "__main__":
    # Wait a bit for server to start if running immediately after start command
    time.sleep(5)
    test_api()
