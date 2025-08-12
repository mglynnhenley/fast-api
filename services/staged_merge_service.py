import os
import requests
import time
import base64
from typing import Optional, Dict, Any, Tuple
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class StagedMergeService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Staged Merge service.
        
        Args:
            api_key: Black Forest API key. If None, will use BFL_API_KEY environment variable
        """
        if api_key is None:
            api_key = os.environ.get("BFL_API_KEY")
        
        if not api_key:
            raise ValueError("Black Forest API key is required. Set BFL_API_KEY environment variable or pass api_key parameter.")
        
        self.api_key = api_key
        self.base_url = "https://api.bfl.ai/v1/flux-kontext-pro"
    
    def encode_image(self, image_path: str) -> str:
        """Encode an image file to base64 string."""
        image = Image.open(image_path)
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()
    
    def call_black_forest_api(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        Call the Black Forest API to edit an image.
        
        Args:
            image_path: Path to the input image file
            prompt: Description of what to edit on the image
        
        Returns:
            Dictionary containing the API response
        """
        # Encode the image
        img_str = self.encode_image(image_path)
        
        # Make the API request
        response = requests.post(
            self.base_url,
            headers={
                'accept': 'application/json',
                'x-key': self.api_key,
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
    
    def poll_for_result(self, polling_url: str, request_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """
        Poll the Black Forest API for the result of an image editing request.
        
        Args:
            polling_url: URL returned from the initial API call
            request_id: Request ID from the initial API call
            max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
        
        Returns:
            Dictionary containing the final result
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(
                    polling_url,
                    headers={
                        'accept': 'application/json',
                        'x-key': self.api_key,
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
    
    def download_and_save_image(self, image_url: str, output_path: str) -> str:
        """
        Download and save an image from a URL.
        
        Args:
            image_url: URL of the image to download
            output_path: Path where to save the image
        
        Returns:
            Path to the saved image
        """
        print(f"Downloading image from: {image_url}")
        
        response = requests.get(image_url)
        if response.status_code == 200:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the image
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Image saved as '{output_path}'")
            return output_path
        else:
            raise Exception(f"Failed to download image: {response.status_code}")
    
    def edit_image(self, image_path: str, prompt: str, second_image_path: str = None) -> str:
        """
        Edit an image using the Black Forest API and return the path to the edited image.
        
        Args:
            image_path: Path to the input image file
            prompt: Description of what to edit on the image
            second_image_path: Optional second image for combination
        
        Returns:
            Path to the saved edited image
        """
        # Check if input image exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image not found: {image_path}")
        
        # If second image is provided, create side-by-side composite manually
        if second_image_path and os.path.exists(second_image_path):
            return self.create_side_by_side_composite(image_path, second_image_path)
        
        # Standard single image editing with API
        response_data = self.call_black_forest_api(image_path, prompt)
        
        # Wait for the result
        request_id = response_data["id"]
        polling_url = response_data["polling_url"]
        
        print(f"Request submitted with ID: {request_id}")
        print("Waiting for result...")
        
        result = self.poll_for_result(polling_url, request_id)
        
        print("Image editing completed!")
        
        # Download and save the result
        if "result" in result and "sample" in result["result"]:
            image_url = result["result"]["sample"]
            timestamp = int(time.time() * 1000)
            output_path = f"output/staged_edit_{timestamp}.jpg"
            return self.download_and_save_image(image_url, output_path)
        else:
            raise Exception("No image URL found in the result")
    
    def create_side_by_side_composite(self, image_path_1: str, image_path_2: str) -> str:
        """
        Create a side-by-side composite of two images using PIL.
        
        Args:
            image_path_1: Path to the first image (left side)
            image_path_2: Path to the second image (right side)
        
        Returns:
            Path to the saved composite image
        """
        print("Creating side-by-side composite manually...")
        
        # Open both images
        img1 = Image.open(image_path_1)
        img2 = Image.open(image_path_2)
        
        # Convert to RGB if necessary
        if img1.mode != 'RGB':
            img1 = img1.convert('RGB')
        if img2.mode != 'RGB':
            img2 = img2.convert('RGB')
        
        # Get dimensions
        width1, height1 = img1.size
        width2, height2 = img2.size
        
        # Calculate target height (use the larger height)
        target_height = max(height1, height2)
        
        # Resize images to have the same height while maintaining aspect ratio
        def resize_maintaining_aspect_ratio(img, target_height):
            width, height = img.size
            aspect_ratio = width / height
            new_width = int(target_height * aspect_ratio)
            return img.resize((new_width, target_height), Image.Resampling.LANCZOS)
        
        img1_resized = resize_maintaining_aspect_ratio(img1, target_height)
        img2_resized = resize_maintaining_aspect_ratio(img2, target_height)
        
        # Calculate total width for composite
        total_width = img1_resized.width + img2_resized.width
        
        # Create new image with white background
        composite = Image.new('RGB', (total_width, target_height), 'white')
        
        # Paste images side by side
        composite.paste(img1_resized, (0, 0))
        composite.paste(img2_resized, (img1_resized.width, 0))
        
        # Save the composite
        timestamp = int(time.time() * 1000)
        output_path = f"output/side_by_side_{timestamp}.jpg"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        composite.save(output_path, 'JPEG', quality=95)
        print(f"Side-by-side composite saved: {output_path}")
        
        return output_path
    
    def staged_merge_with_kontext(self, image_a_path: str, image_b_path: str, 
                                 add_person_prompt: str, composite_prompt: str, 
                                 swap_prompt: str) -> Dict[str, str]:
        """
        Perform staged person swap with context preservation: 
        add person to image 1 → composite images → swap people
        
        Args:
            image_a_path: Path to the context image (background scene)
            image_b_path: Path to the person source image
            add_person_prompt: Prompt to add someone doing something to image 1
            composite_prompt: Prompt to composite the images
            swap_prompt: Prompt to swap the people in the final image
        
        Returns:
            Dictionary containing paths to all generated images
        """
        print("🚀 Starting Staged Merge with Kontext")
        print("=" * 50)
        
        # Validate input images exist
        if not os.path.exists(image_a_path):
            raise FileNotFoundError(f"Context image not found: {image_a_path}")
        if not os.path.exists(image_b_path):
            raise FileNotFoundError(f"Person source image not found: {image_b_path}")
        
        results = {}
        
        try:
            # Step 1: Add someone doing something to image 1 (don't change background)
            print("👤 Step 1: Adding Person to Image 1")
            print(f"Prompt: {add_person_prompt}")
            print(f"Adding person to: {image_a_path}")
            person_added_path = self.edit_image(image_a_path, add_person_prompt)
            results['person_added'] = person_added_path
            print(f"✅ Person added to image: {person_added_path}")
            
            # Step 2: Create side-by-side composite
            print("\n🖼️ Step 2: Creating Side-by-Side Composite")
            print(f"Placing {person_added_path} and {image_b_path} side by side")
            composite_path = self.edit_image(person_added_path, composite_prompt, image_b_path)
            results['composite'] = composite_path
            print(f"✅ Side-by-side composite created: {composite_path}")
            
            # Step 3: Swap the people and show image 1 with person swapped
            print("\n🔄 Step 3: Swapping People")
            print(f"Prompt: {swap_prompt}")
            print("Performing person swap from composite image...")
            
            # Enhanced prompt with more context about the composite structure
            enhanced_swap_prompt = f"{swap_prompt} The composite image has two parts: LEFT (scene with person) and RIGHT (person source). Transfer the person's appearance from RIGHT to LEFT, keeping the LEFT scene intact. Return only the LEFT side result."
            final_swap_path = self.edit_image(composite_path, enhanced_swap_prompt)
            results['final_swap'] = final_swap_path
            print(f"✅ Person swap completed: {final_swap_path}")
            
            print("\n" + "=" * 50)
            print("📋 PERSON SWAP RESULTS:")
            print(f"   • Original Image: {image_a_path}")
            print(f"   • Person Source: {image_b_path}")
            print(f"   • Person Added: {results['person_added']}")
            print(f"   • Composite: {results['composite']}")
            print(f"   • Final Swap: {results['final_swap']}")
            print("✅ Person swap completed successfully!")
            
            return results
            
        except Exception as e:
            print(f"❌ Staged merge failed: {e}")
            print(f"Current results: {results}")
            raise


def main():
    """
    Example usage of the Staged Merge service.
    """
    try:
        # Initialize the service
        service = StagedMergeService()
        
        # Example configuration - use correct image paths
        image_a = "output/1.jpg"  # Picture 1 (scene/background image)
        image_b = "input/person.jpeg"  # Picture 2 (person to swap INTO the scene)
        
        # Check if input images exist
        if not os.path.exists(image_a):
            print(f"❌ Image A not found: {image_a}")
            return
        
        if not os.path.exists(image_b):
            print(f"❌ Image B not found: {image_b}")
            return
        
        # Staged merge prompts - 3-step person swap workflow
        add_person_prompt = "Add a realistic person to this scene in a natural pose. The person should be doing something interesting but believable. Keep the background, lighting, and environment exactly as they are. Only add the person, do not change anything else in the image."
        composite_prompt = "Create a side-by-side comparison by placing the first image on the left and the second image on the right, with equal spacing and the same height. Make it look like a before/after or comparison layout."
        swap_prompt = "This is a side-by-side composite image. I need you to: 1) Take the person's appearance from the RIGHT side image, 2) Apply that person's appearance to the person on the LEFT side, 3) Keep the LEFT side background, pose, and scene exactly as they are, 4) Only change the person's appearance, not the environment, 5) Return ONLY the left side image with the updated person. The result should be the left side scene with the right side person's appearance."
        
        # Perform staged merge
        results = service.staged_merge_with_kontext(
            image_a_path=image_a,
            image_b_path=image_b,
            add_person_prompt=add_person_prompt,
            composite_prompt=composite_prompt,
            swap_prompt=swap_prompt
        )
        
        print(f"\n🎯 Final result: {results['final_swap']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
