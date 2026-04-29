import requests
import json
import time

url = "http://127.0.0.1:8000/generate"
payload = {
    "prompt": "Create a simple task management system. There should be a User, and Tasks that belong to the User. Users can login with an email and password. Admins can delete users. Please make sure the password must be at least 8 characters."
}

print(f"Sending request to {url}...")
start = time.time()
try:
    response = requests.post(url, json=payload, timeout=120)
    data = response.json()
    print(f"Time taken: {time.time() - start:.2f}s")
    
    with open('test_output.json', 'w') as f:
        json.dump(data, f, indent=2)
        
    print("Saved output to test_output.json")
    
    # Print the logs
    print("\n--- PIPELINE LOGS ---")
    for log in data.get('logs', []):
        print(log)
        
except Exception as e:
    print(f"Error: {e}")
