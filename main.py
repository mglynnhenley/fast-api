import os
import time
from services.street_view_service import StreetViewService
from services.black_forest_api import process_image_with_prompt
from services.staged_merge_service import StagedMergeService


def get_street_view_360(location: str, degrees: list = [0, 90, 180, 270], size: str = '1024x768') -> dict:
    """
    Get Street View images at multiple angles around a location.
    
    Args:
        location: Address or coordinates
        degrees: List of angles to capture (default: [0, 90, 180, 270])
        size: Image size (default: '1024x768')
    
    Returns:
        Dictionary containing results for each angle
    """
    print(f"🗺️  Getting Street View images for: {location}")
    print(f"📐 Angles: {degrees}")
    
    service = StreetViewService()
    results = service.get_street_view_at_degrees(location, degrees, size)
    
    # Save images and collect results
    saved_images = []
    for i, result in enumerate(results):
        if result['success']:
            # Generate filename with number (1,2,3,4 for Street View images)
            image_number = i + 1  # Start from 1, AI will overwrite 1 later
            filename = f"{image_number}.jpg"
            filepath = f"output/{filename}"
            
            # Ensure output directory exists
            os.makedirs("output", exist_ok=True)
            
            # Save the image
            with open(filepath, 'wb') as f:
                f.write(result['imageBuffer'])
            
            image_data = {
                'angle': degrees[i],
                'filepath': filepath,
                'url': result['url'],
                'success': True
            }
            
            saved_images.append(image_data)
            
            print(f"✅ {degrees[i]}°: Saved to {filepath}")
        else:
            print(f"❌ {degrees[i]}°: {result['error']}")
            saved_images.append({
                'angle': degrees[i],
                'success': False,
                'error': result['error']
            })
    
    return {
        'location': location,
        'images': saved_images,
        'total_captured': len([img for img in saved_images if img['success']])
    }




def process_with_ai(image_path: str, prompt: str) -> str:
    """
    Process an image with Black Forest Labs AI.
    
    Args:
        image_path: Path to the input image
        prompt: AI editing prompt
    
    Returns:
        Path to the processed image
    """
    print(f"🤖 Processing image with AI: {prompt}")
    
    try:
        output_path = process_image_with_prompt(image_path, prompt)
        print(f"✅ AI processing complete: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ AI processing failed: {e}")
        raise


def perform_staged_merge(image_a_path: str, image_b_path: str, person_description: str) -> dict:
    """
    Perform staged merge with Kontext for person swapping.
    
    Args:
        image_a_path: Path to the context image (person doing action)
        image_b_path: Path to the person source image
        person_description: Description of what the person is doing
    
    Returns:
        Dictionary containing paths to all generated images
    """
    print(f"🔄 Starting Staged Merge for person swap")
    print(f"Context: {person_description}")
    
    try:
        service = StagedMergeService()
        
        # Customize prompts for person swapping with image combination
        edit_prompt = f"Combine the person from {image_b_path} with the background and context from {image_a_path}, place the person naturally in the scene"
        composite_prompt = "Enhance the person's appearance, improve lighting and details while maintaining the natural look"
        blend_prompt = "Refine the person placement and ensure seamless integration with the background context"
        
        results = service.staged_merge_with_kontext(
            image_a_path=image_a_path,
            image_b_path=image_b_path,
            edit_prompt=edit_prompt,
            composite_prompt=composite_prompt,
            blend_prompt=blend_prompt
        )
        
        print(f"✅ Staged merge completed: {results['final_blend']}")
        return results
        
    except Exception as e:
        print(f"❌ Staged merge failed: {e}")
        raise

def main():
    """
    Main function that gets Street View images and processes one with AI.
    """
    try:
        # Configuration
        location = "London Eye, London, UK"  # London Eye
        angles = [0, 90, 180, 270]  # Four cardinal directions
        ai_prompt = "5 ducks on the pavement"  # AI editing prompt
        
        # Staged merge configuration
        enable_staged_merge = True  # Set to False to skip staged merge
        person_description = "A person is standing in front of the london ai"  # Describe what the person is doing
        
        print("🚀 Starting Street View + AI Processing Pipeline")
        print("=" * 50)
        
        # Step 1: Get Street View images at multiple angles
        street_view_results = get_street_view_360(location, angles)
        
        print(f"\n📊 Street View Results:")
        print(f"Location: {street_view_results['location']}")
        print(f"Images captured: {street_view_results['total_captured']}/{len(angles)}")
        

        
        # Step 2: Process one image with AI (use the first successful image)
        successful_images = [img for img in street_view_results['images'] if img['success']]
        
        if not successful_images:
            print("❌ No Street View images were captured successfully")
            return
        
        # Use the first successful image for AI processing
        selected_image = successful_images[0]
        print(f"\n🎯 Selected image for AI processing: {selected_image['angle']}°")
        
        # Step 3: Process with AI (save as 1.jpg)
        ai_processed_path = process_with_ai(selected_image['filepath'], ai_prompt)
        
        # Rename AI image to 1.jpg if it's not already named that
        if not ai_processed_path.endswith("1.jpg"):
            new_ai_path = "output/1.jpg"
            import shutil
            shutil.move(ai_processed_path, new_ai_path)
            ai_processed_path = new_ai_path
        
        # Step 4: Perform staged merge (optional)
        staged_merge_results = None
        if enable_staged_merge:
            print(f"\n🔄 Step 4: Performing Staged Merge")
            
            # Use person.jpeg from input folder as the person source image
            person_source_path = "input/person.jpeg"
            
            if os.path.exists(person_source_path):
                print(f"Using context image: {successful_images[0]['filepath']}")
                print(f"Using person source: {person_source_path}")
                
                try:
                    staged_merge_results = perform_staged_merge(
                        image_a_path=successful_images[0]['filepath'],  # Context image (Street View)
                        image_b_path=person_source_path,  # Person source image from input
                        person_description=person_description
                    )
                    print(f"✅ Staged merge successful!")
                except Exception as e:
                    print(f"⚠️  Staged merge failed, continuing with main pipeline: {e}")
            else:
                print(f"⚠️  Person source image not found: {person_source_path}")
                print(f"⏭️  Skipping Staged Merge")
        else:
            print(f"\n⏭️  Step 4: Skipping Staged Merge (disabled)")
        
        # Step 5: Ensure all 4 images are generated
        print(f"\n📋 Generating all 4 images:")
        print(f"   • 1.jpg: AI Enhanced Image ✓")
        for i, img in enumerate(street_view_results['images']):
            if img['success']:
                image_num = i + 2
                print(f"   • {image_num}.jpg: Street View {img['angle']}° ✓")
            else:
                image_num = i + 2
                print(f"   • {image_num}.jpg: Failed - {img['error']} ❌")
        
        # Step 4: Summary
        print("\n" + "=" * 50)
        print("📋 FINAL RESULTS:")
        print(f"📍 Location: {location}")
        print(f"📸 Images Saved:")
        print(f"   • 1.jpg: AI Enhanced Image (from {selected_image['angle']}°)")
        for img in street_view_results['images']:
            if img['success']:
                image_num = street_view_results['images'].index(img) + 1
                print(f"   • {image_num}.jpg: Street View {img['angle']}°")
            else:
                image_num = street_view_results['images'].index(img) + 1
                print(f"   • {image_num}.jpg: Failed - {img['error']}")
        
        print(f"🤖 AI Processing Details:")
        print(f"   • Original: {selected_image['filepath']}")
        print(f"   • AI Enhanced: {ai_processed_path}")
        print(f"   • Prompt: '{ai_prompt}'")
        
        # Staged merge results
        if staged_merge_results:
            print(f"\n🔄 Staged Merge Results:")
            print(f"   • Context Preserved: {staged_merge_results['edited_a']}")
            print(f"   • Person Enhanced: {staged_merge_results['composite_b']}")
            print(f"   • Final Person Swap: {staged_merge_results['final_blend']}")
            print(f"   • Person Description: '{person_description}'")
        
        print("\n✅ Pipeline completed successfully!")
        
        # Return the results for programmatic use
        return {
            'location': location,
            'street_view_images': street_view_results['images'],
            'ai_processed_image': ai_processed_path,
            'ai_prompt': ai_prompt,
            'staged_merge_results': staged_merge_results
        }
        
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")
        return None


if __name__ == "__main__":
    main()
