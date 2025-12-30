#!/usr/bin/env python3
"""
Test script for perspective generation endpoint
Tests the /api/generate-perspective endpoint
"""
import requests
import json
import sys

API_BASE_URL = "http://localhost:8000"

def test_generate_perspective():
    """Test generating a perspective from a query"""
    print("=" * 60)
    print("Testing Perspective Generation Endpoint")
    print("=" * 60)
    
    # Test data
    payload = {
        "query": "What are Carl Pei's views on technology and innovation?",
        "top_k": 5
    }
    
    print(f"\nRequest payload:")
    print(json.dumps(payload, indent=2))
    
    try:
        print(f"\nSending POST request to {API_BASE_URL}/api/generate-perspective...")
        response = requests.post(
            f"{API_BASE_URL}/api/generate-perspective",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 minutes timeout for LLM generation
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✓ Success!")
            print(f"\nQuery: {result.get('query', 'N/A')}")
            print(f"\nPerspective:")
            print("-" * 60)
            print(result.get('perspective', 'N/A'))
            print("-" * 60)
            
            if result.get('sources'):
                print(f"\nSources ({len(result['sources'])}):")
                for i, source in enumerate(result['sources'], 1):
                    print(f"\n  {i}. Category: {source.get('category', 'N/A')}")
                    print(f"     Summary: {source.get('summary', 'N/A')[:100]}...")
                    if 'relevance_score' in source:
                        print(f"     Relevance: {source['relevance_score']:.4f}")
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
    test_generate_perspective()

