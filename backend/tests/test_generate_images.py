#!/usr/bin/env python3
"""
Test script for image generation endpoint
Tests the /api/generate endpoint
"""
import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"

def test_generate_images():
    """Test generating images from Instagram summary"""
    print("=" * 60)
    print("Testing Image Generation Endpoint")
    print("=" * 60)
    
    # Test data - requires that profile state exists with Instagram analysis
    payload = {
        "name": "Carl Pei",
        "number_of_images": 3
    }
    
    print(f"\nRequest payload:")
    print(json.dumps(payload, indent=2))
    print("\nNote: This requires:")
    print("  1. Profile state to exist for the person")
    print("  2. Instagram analysis to be completed (scrape Instagram first)")
    print("  3. Profile image to exist from search")
    
    try:
        print(f"\nSending POST request to {API_BASE_URL}/api/generate...")
        response = requests.post(
            f"{API_BASE_URL}/api/generate",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=600  # 10 minutes timeout for image generation
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✓ Success!")
            print(f"\nResponse:")
            print(json.dumps(result, indent=2))
            
            if result.get("generated_images"):
                print(f"\n✓ Generated {len(result['generated_images'])} images:")
                for i, filename in enumerate(result['generated_images'], 1):
                    print(f"  {i}. {filename}")
                
                if result.get("prompt"):
                    print(f"\nGenerated Prompt:")
                    print("-" * 60)
                    print(result['prompt'])
                    print("-" * 60)
            else:
                print("\n⚠ No images were generated")
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
    test_generate_images()

