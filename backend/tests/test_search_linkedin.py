#!/usr/bin/env python3
"""
Test script for LinkedIn search endpoint
Tests the LinkedIn search functionality of /api/search-profiles
"""
import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"

def test_search_linkedin():
    """Test searching for LinkedIn profiles"""
    print("=" * 60)
    print("Testing LinkedIn Search Endpoint")
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
            
            if result.get("linkedin"):
                print(f"\n✓ Found LinkedIn profile:")
                print(f"  URL: {result['linkedin'].get('profile_url', 'N/A')}")
                print(f"  All URLs: {len(result['linkedin'].get('all_urls', []))} found")
            else:
                print("\n⚠ No LinkedIn profile found")
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
    test_search_linkedin()

