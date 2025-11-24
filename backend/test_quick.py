import requests
import json

try:
    response = requests.post(
        "http://localhost:8000/recommend",
        json={"query": "Java developer", "top_k": 5}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
