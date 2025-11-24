#!/usr/bin/env python3
"""Test session creation via NLB"""

import requests
import json
import time

# NLB URL
NLB_URL = "http://ad171b9bedd35460890473e6baf67a42-b4ef754c96f0229e.elb.ap-south-1.amazonaws.com"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{NLB_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_session_creation():
    """Test session creation"""
    print("\nTesting session creation...")
    session_id = f"test-nlb-{int(time.time())}"
    
    try:
        response = requests.post(
            f"{NLB_URL}/sessions",
            json={"session_id": session_id},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Dynamic Pod Lifecycle System via NLB")
    print("=" * 60)
    
    # Test health
    health_ok = test_health()
    
    if health_ok:
        # Test session creation
        session_ok = test_session_creation()
        
        if session_ok:
            print("\n✅ ALL TESTS PASSED!")
        else:
            print("\n❌ Session creation failed")
    else:
        print("\n❌ Health check failed")
