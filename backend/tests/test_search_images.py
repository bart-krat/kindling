#!/usr/bin/env python3
"""
Test script for image search endpoint
Tests the image search functionality of /api/search-profiles
"""
import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"

def test_search_images():
    """Test searching for profile images"""
    print("=" * 60)
    print("Testing Image Search Endpoint")
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
            
            if result.get("image"):
                print(f"\n✓ Found profile image:")
                print(f"  Filename: {result['image'].get('filename', 'N/A')}")
                print(f"  URL: {result['image'].get('url', 'N/A')}")
                print(f"  Title: {result['image'].get('title', 'N/A')}")
                print(f"  Source: {result['image'].get('source', 'N/A')}")
            else:
                print("\n⚠ No profile image found")
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
    test_search_images()

