#!/usr/bin/env python3
"""
Test script for the Street View AI Processing API
"""

import requests
import json
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_process_streetview():
    """Test the main Street View processing endpoint"""
    print("🗺️ Testing Street View processing...")
    
    # Test data
    data = {
        "address": "Times Square, New York, NY",
        "prompt": "Add a giant robot walking down the street",
        "angles": [0, 90, 180, 270]
    }
    
    print(f"Address: {data['address']}")
    print(f"Prompt: {data['prompt']}")
    print(f"Angles: {data['angles']}")
    print()
    
    # Make the request
    response = requests.post(
        f"{BASE_URL}/process-streetview",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Session ID: {result['session_id']}")
        print(f"Status: {result['status']}")
        print(f"Total images captured: {result['results']['total_captured']}")
        print(f"AI processed image: {result['results']['ai_processed']}")
        print()
        
        # List all street view images
        print("Street View Images:")
        for img in result['results']['street_view_images']:
            status = "✅" if img['success'] else "❌"
            print(f"  {status} {img['angle']}°: {img['filepath']}")
        
        return result['session_id']
    else:
        print(f"Error: {response.text}")
        return None

def test_session_info(session_id):
    """Test getting session information"""
    print(f"\n📋 Testing session info for {session_id}...")
    
    response = requests.get(f"{BASE_URL}/sessions/{session_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Files available: {result['files_available']}")
    else:
        print(f"Error: {response.text}")

def test_download_image(session_id, image_name):
    """Test downloading an image"""
    print(f"\n⬇️ Testing download for {image_name}...")
    
    response = requests.get(f"{BASE_URL}/download/{session_id}/{image_name}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        # Save the image
        filename = f"downloaded_{image_name}"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"✅ Image saved as {filename}")
    else:
        print(f"Error: {response.text}")

def main():
    """Run all tests"""
    print("🚀 Starting Street View API Tests")
    print("=" * 50)
    
    # Test health
    test_health()
    
    # Test processing
    session_id = test_process_streetview()
    
    if session_id:
        # Test session info
        test_session_info(session_id)
        
        # Test downloading images
        test_download_image(session_id, "1_ai_processed")
        test_download_image(session_id, "1")
        test_download_image(session_id, "2")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
