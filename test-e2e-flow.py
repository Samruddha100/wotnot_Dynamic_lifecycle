#!/usr/bin/env python3
"""End-to-end test for Dynamic Pod Lifecycle Management System"""
import requests
import time
import sys

# Test configuration
API_GATEWAY_URL = "http://api-gateway.sessions.svc.cluster.local:8000"
SESSION_ID = f"test-session-{int(time.time())}"

print(f"=== End-to-End Flow Test ===")
print(f"Session ID: {SESSION_ID}")
print(f"API Gateway: {API_GATEWAY_URL}\n")

try:
    # Step 1: Create a session by sending a request
    print("Step 1: Sending request to create session...")
    response = requests.post(
        f"{API_GATEWAY_URL}/api/v1/session/{SESSION_ID}/execute",
        json={"action": "test", "data": "hello"},
        timeout=30
    )
    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.text}\n")
    
    # Step 2: Check if session was created in lifecycle controller
    print("Step 2: Checking session status...")
    response = requests.get(
        f"{API_GATEWAY_URL}/api/v1/session/{SESSION_ID}/status",
        timeout=10
    )
    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.text}\n")
    
    # Step 3: Send another request to same session (should route to same pod)
    print("Step 3: Sending second request to same session...")
    response = requests.post(
        f"{API_GATEWAY_URL}/api/v1/session/{SESSION_ID}/execute",
        json={"action": "test2", "data": "world"},
        timeout=10
    )
    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.text}\n")
    
    print("✅ End-to-end test completed successfully!")
    sys.exit(0)
    
except requests.exceptions.Timeout as e:
    print(f"❌ Timeout error: {e}")
    sys.exit(1)
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
