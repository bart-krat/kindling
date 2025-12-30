#!/usr/bin/env python3
"""
Test script for LinkedIn scraping endpoint
Tests the LinkedIn scraping functionality of /api/scrape-profiles
"""
import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"

def test_scrape_linkedin():
    """Test scraping LinkedIn posts"""
    print("=" * 60)
    print("Testing LinkedIn Scraping Endpoint")
    print("=" * 60)
    
    # Test data - using Carl Pei's LinkedIn profile
    payload = {
        "linkedin_url": "https://uk.linkedin.com/in/getpeid",
        "name": "Carl Pei"
    }
    
    print(f"\nRequest payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        print(f"\nSending POST request to {API_BASE_URL}/api/scrape-profiles...")
        print("Note: This will open a browser window for LinkedIn login")
        
        response = requests.post(
            f"{API_BASE_URL}/api/scrape-profiles",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=600  # 10 minutes timeout for scraping (LinkedIn can be slow)
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✓ Success!")
            print(f"\nResponse:")
            print(json.dumps(result, indent=2))
            
            if result.get("linkedin_count", 0) > 0:
                print(f"\n✓ Scraped {result['linkedin_count']} LinkedIn posts")
                print(f"  Saved to: {result.get('linkedin_file', 'N/A')}")
            else:
                print("\n⚠ No LinkedIn posts were scraped")
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
    test_scrape_linkedin()

