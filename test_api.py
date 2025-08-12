#!/usr/bin/env python3
"""
Test script for the FastAPI endpoints
"""
import requests
import os
from pathlib import Path

# API base URL (change this to your Railway URL when deployed)
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_root():
    """Test the root endpoint"""
    print("Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_process_images():
    """Test the image processing endpoint"""
    print("Testing image processing...")
    
    # Check if test images exist
    background_path = "input/background.jpg"  # You'll need to add this
    person_path = "input/person.jpeg"
    
    if not os.path.exists(background_path):
        print(f"Background image not found: {background_path}")
        print("Please add a background image to test this endpoint")
        return
    
    if not os.path.exists(person_path):
        print(f"Person image not found: {person_path}")
        print("Please add a person image to test this endpoint")
        return
    
    # Prepare files for upload
    files = {
        'background_image': open(background_path, 'rb'),
        'person_image': open(person_path, 'rb')
    }
    
    # Custom prompts (optional)
    data = {
        'add_person_prompt': 'Add a realistic person to this scene in a natural pose',
        'composite_prompt': 'Create a side-by-side comparison',
        'swap_prompt': 'Take the person appearance from the right side and apply to the left side'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/process-images", files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get('session_id')
            print(f"Session ID: {session_id}")
            print("Files generated:")
            for file_type, path in result.get('results', {}).items():
                print(f"  - {file_type}: {path}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Close files
        for file in files.values():
            file.close()
    
    print()

def test_docs():
    """Test if the API docs are accessible"""
    print("Testing API documentation...")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ API documentation is accessible")
        else:
            print("❌ API documentation not accessible")
    except Exception as e:
        print(f"Error accessing docs: {e}")
    print()

if __name__ == "__main__":
    print("🚀 Testing FastAPI Image Processing Service")
    print("=" * 50)
    
    test_health()
    test_root()
    test_docs()
    test_process_images()
    
    print("✅ Testing completed!")
    print(f"📖 API Documentation: {BASE_URL}/docs")
    print(f"🔍 Interactive API: {BASE_URL}/redoc")
