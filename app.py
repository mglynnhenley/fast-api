from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import base64
from typing import List
import uuid
from services.street_view_service import StreetViewService
from services.black_forest_api import process_image_with_prompt
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Street View AI Processing API",
    description="API for getting Street View images and processing with Black Forest Labs AI",
    version="1.0.0"
)

# Add CORS middleware for public access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
)

# Initialize services
street_view_service = StreetViewService()

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

def encode_image_to_base64(filepath: str) -> str:
    """Encode an image file to base64 string"""
    try:
        with open(filepath, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
    except Exception as e:
        logger.error(f"Error encoding image {filepath}: {str(e)}")
        return ""

class ProcessRequest(BaseModel):
    address: str
    prompt: str
    angles: List[int] = [0, 90, 180, 270]  # Default to 4 cardinal directions

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Street View AI Processing API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    import socket
    try:
        # Get local IP address
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "unknown"
    
    return {
        "status": "healthy",
        "service": "Street View AI Processing API",
        "version": "1.0.0",
        "local_ip": local_ip,
        "port": int(os.environ.get("PORT", 8000)),
        "public_url": f"http://{local_ip}:{os.environ.get('PORT', 8000)}"
    }

@app.post("/process-streetview")
async def process_streetview(request: ProcessRequest):
    """
    Process Street View images with AI
    
    - **address**: The address to get Street View images for
    - **prompt**: AI editing prompt for the first image
    - **angles**: List of angles to capture (default: [0, 90, 180, 270])
    """
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        session_dir = f"output/{session_id}"
        os.makedirs(session_dir, exist_ok=True)
        
        logger.info(f"Processing session {session_id} for address: {request.address}")
        
        # Step 1: Get Street View images at multiple angles
        print(f"🗺️  Getting Street View images for: {request.address}")
        print(f"📐 Angles: {request.angles}")
        
        street_view_results = street_view_service.get_street_view_at_degrees(
            request.address, 
            request.angles, 
            '1024x768'
        )
        
        # Save images and collect results
        saved_images = []
        for i, result in enumerate(street_view_results):
            if result['success']:
                # Generate filename with number (1,2,3,4 for Street View images)
                image_number = i + 1
                filename = f"{image_number}.jpg"
                filepath = f"{session_dir}/{filename}"
                
                # Save the image
                with open(filepath, 'wb') as f:
                    f.write(result['imageBuffer'])
                
                image_data = {
                    'angle': request.angles[i],
                    'filepath': filepath,
                    'url': result['url'],
                    'success': True
                }
                
                saved_images.append(image_data)
                
                print(f"✅ {request.angles[i]}°: Saved to {filepath}")
            else:
                print(f"❌ {request.angles[i]}°: {result['error']}")
                saved_images.append({
                    'angle': request.angles[i],
                    'success': False,
                    'error': result['error']
                })
        
        # Step 2: Process the first successful image with AI
        successful_images = [img for img in saved_images if img['success']]
        
        if not successful_images:
            raise HTTPException(status_code=400, detail="No Street View images were captured successfully")
        
        # Use the first successful image for AI processing
        selected_image = successful_images[0]
        print(f"\n🎯 Selected image for AI processing: {selected_image['angle']}°")
        
        # Process with AI
        print(f"🤖 Processing image with AI: {request.prompt}")
        ai_processed_path = process_image_with_prompt(selected_image['filepath'], request.prompt)
        print(f"✅ AI processing complete: {ai_processed_path}")
        
        # Copy AI processed image to session directory as 1.jpg (replacing the original)
        ai_session_path = f"{session_dir}/1.jpg"
        shutil.copy2(ai_processed_path, ai_session_path)

        base64_encoded_images = []
        for i in range(1, 5):
            image_path = f"{session_dir}/{i}.jpg"
            if os.path.exists(image_path):
                base64_encoded_images.append(encode_image_to_base64(image_path))
            else:
                base64_encoded_images.append(None)
        
        # Return results
        return {
            "session_id": session_id,
            "status": "completed",
            "address": request.address,
            "prompt": request.prompt,
            "results": {
                "images": [
                    {
                        "number": i + 1,
                        "angle": img['angle'],
                        "filepath": img['filepath'],
                        "success": img['success'],
                        "ai_processed": i == 0,  # First image is AI processed
                        "base64_encoded": base64_encoded_images[i]
                    } for i, img in enumerate(saved_images)
                ],
                "total_captured": len(successful_images)
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing streetview: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/download/{session_id}/{image_number}")
async def download_image(session_id: str, image_number: str):
    """
    Download a specific image from a processing session
    
    - **session_id**: The session ID from processing
    - **image_number**: Image number (1, 2, 3, 4) - where 1 is AI processed
    """
    try:
        # Construct file path
        file_path = f"output/{session_id}/{image_number}.jpg"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Image not found: {image_number}")
        
        return FileResponse(
            path=file_path,
            filename=f"{image_number}_{session_id}.jpg",
            media_type="image/jpeg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """
    Get information about a processing session
    
    - **session_id**: The session ID to query
    """
    try:
        session_dir = f"output/{session_id}"
        
        if not os.path.exists(session_dir):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # List all files in session directory
        files = []
        for filename in os.listdir(session_dir):
            if filename.endswith('.jpg'):
                files.append(filename)
        
        return {
            "session_id": session_id,
            "files_available": files,
            "session_dir": session_dir
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}")

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a processing session and all its files
    
    - **session_id**: The session ID to delete
    """
    try:
        session_dir = f"output/{session_id}"
        
        if not os.path.exists(session_dir):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Remove the entire session directory
        shutil.rmtree(session_dir)
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Run on all interfaces for public access
    uvicorn.run(
        app, 
        host="0.0.0.0",  # Allow external connections
        port=int(os.environ.get("PORT", 8000)),
        access_log=True,  # Enable access logging
        log_level="info"
    )
