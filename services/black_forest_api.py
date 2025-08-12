import os
import requests
import base64
import time
from PIL import Image
from io import BytesIO
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def encode_image(image_path: str) -> str:
    """Encode an image file to base64 string."""
    image = Image.open(image_path)
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()


def call_black_forest_api(image_path: str, prompt: str, api_key: Optional[str] = None) -> dict:
    """
    Call the Black Forest API to edit an image.
    
    Args:
        image_path: Path to the input image file
        prompt: Description of what to edit on the image
        api_key: API key for Black Forest. If None, will use BFL_API_KEY environment variable
    
    Returns:
        Dictionary containing the API response
    """
    if api_key is None:
        api_key = os.environ.get("BFL_API_KEY")
    
    if not api_key:
        raise ValueError("API key is required. Set BFL_API_KEY environment variable or pass api_key parameter.")
    
    # Encode the image
    img_str = encode_image(image_path)
    
    # Make the API request
    response = requests.post(
        'https://api.bfl.ai/v1/flux-kontext-pro',
        headers={
            'accept': 'application/json',
            'x-key': api_key,
            'Content-Type': 'application/json',
        },
        json={
            'prompt': prompt,
            'input_image': img_str,
        },
    )
    
    if response.status_code != 200:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")
    
    return response.json()


def poll_for_result(polling_url: str, request_id: str, api_key: Optional[str] = None, max_wait_time: int = 300) -> dict:
    """
    Poll the Black Forest API for the result of an image editing request.
    
    Args:
        polling_url: URL returned from the initial API call
        request_id: Request ID from the initial API call
        api_key: API key for Black Forest. If None, will use BFL_API_KEY environment variable
        max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
    
    Returns:
        Dictionary containing the final result
    """
    if api_key is None:
        api_key = os.environ.get("BFL_API_KEY")
    
    if not api_key:
        raise ValueError("API key is required. Set BFL_API_KEY environment variable or pass api_key parameter.")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            response = requests.get(
                polling_url,
                headers={
                    'accept': 'application/json',
                    'x-key': api_key,
                },
                params={'id': request_id}
            )
            
            if response.status_code != 200:
                raise Exception(f"Polling request failed with status {response.status_code}: {response.text}")
            
            result = response.json()
            
            # Check if the job is complete
            if result.get("status") == "Ready":
                print(f"Image ready: {result.get('result', {}).get('sample', 'No sample URL provided')}")
                return result
            elif result.get("status") in ["Error", "Failed"]:
                raise Exception(f"Image editing failed: {result}")
            
            # Show polling status
            elapsed = int(time.time() - start_time)
            print(f"Polling... (elapsed: {elapsed}s, status: {result.get('status', 'unknown')})")
            
            # Wait before polling again
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(1)
    
    raise TimeoutError(f"Image editing did not complete within {max_wait_time} seconds")


def edit_image(image_path: str, prompt: str, api_key: Optional[str] = None, wait_for_result: bool = True) -> dict:
    """
    Edit an image using the Black Forest API.
    
    Args:
        image_path: Path to the input image file
        prompt: Description of what to edit on the image
        api_key: API key for Black Forest. If None, will use BFL_API_KEY environment variable
        wait_for_result: Whether to wait for the result or return immediately
    
    Returns:
        Dictionary containing the API response or final result
    """
    # Initial API call
    response = call_black_forest_api(image_path, prompt, api_key)
    
    if not wait_for_result:
        return response
    
    # Wait for the result
    request_id = response["id"]
    polling_url = response["polling_url"]
    
    print(f"Request submitted with ID: {request_id}")
    print("Waiting for result...")
    
    result = poll_for_result(polling_url, request_id, api_key)
    
    print("Image editing completed!")
    return result


def process_image_with_prompt(image_path: str, prompt: str) -> str:
    """
    Process an image with a specific prompt and return the output path.
    
    Args:
        image_path: Path to the input image
        prompt: The editing prompt
    
    Returns:
        Path to the saved edited image
    """
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file '{image_path}' not found.")
        
        # Call the API
        result = edit_image(image_path, prompt)
        
        # Save the result image
        if "result" in result and "sample" in result["result"]:
            image_url = result["result"]["sample"]
            print(f"Downloading image from: {image_url}")
            
            # Download the image
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                # Generate filename as 1.jpg for AI image
                filename = "1.jpg"
                
                # Save the image to output folder
                output_path = f"output/{filename}"
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                print(f"Edited image saved as '{output_path}'")
                return output_path
            else:
                raise Exception(f"Failed to download image: {img_response.status_code}")
        else:
            raise Exception("No image URL found in the result")
            
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    # Example usage
    try:
        # Example 1: Basic usage
        image_path = "input/angle_0deg_1754947637605_streetview.jpg"
        prompt = "Add an elephant and a duck"
        
        # Create output directory if it doesn't exist
        os.makedirs("output", exist_ok=True)
       
        output_path = process_image_with_prompt(image_path, prompt)
        print(f"✅ Success! Image saved to: {output_path}")
        # Example 2: Different prompt
        # output_path = process_image_with_prompt("input/another_image.jpg", "Add five dancing cats")
        # print(f"✅ Success! Image saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
