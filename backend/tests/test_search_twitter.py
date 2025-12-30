#!/usr/bin/env python3
"""
Test script for Twitter/X search endpoint
Tests the Twitter/X search functionality of /api/search-profiles
"""
import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"

def test_search_twitter():
    """Test searching for Twitter/X profiles"""
    print("=" * 60)
    print("Testing Twitter/X Search Endpoint")
    print("=" * 60)
    
    # Test data
    payload = {
        "name": "Carl Pei",
        "top_n": 2
    }
    
    print(f"\nRequest payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        print(f"\nSending POST request to {API_BASE_URL}/api/search-profiles...")
        response = requests.post(
            f"{API_BASE_URL}/api/search-profiles",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✓ Success!")
            print(f"\nResponse:")
            print(json.dumps(result, indent=2))
            
            if result.get("twitter"):
                print(f"\n✓ Found Twitter/X profile:")
                print(f"  URL: {result['twitter'].get('profile_url', 'N/A')}")
                print(f"  Username: {result['twitter'].get('username', 'N/A')}")
                print(f"  User ID: {result['twitter'].get('user_id', 'N/A')}")
            else:
                print("\n⚠ No Twitter/X profile found")
        else:
            print(f"\n✗ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to API server")
        print("  Make sure the server is running: uvicorn main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_search_twitter()

