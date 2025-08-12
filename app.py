from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from typing import Dict, Any
import uuid
from services.staged_merge_service import StagedMergeService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Image Processing API",
    description="API for staged image merging and person swapping",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the service
staged_merge_service = StagedMergeService()

# Ensure output directory exists
os.makedirs("output", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Image Processing API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "Image Processing API",
        "version": "1.0.0"
    }

@app.post("/process-images")
async def process_images(
    background_image: UploadFile = File(...),
    person_image: UploadFile = File(...),
    add_person_prompt: str = "Add a realistic person to this scene in a natural pose. The person should be doing something interesting but believable. Keep the background, lighting, and environment exactly as they are. Only add the person, do not change anything else in the image.",
    composite_prompt: str = "Create a side-by-side comparison by placing the first image on the left and the second image on the right, with equal spacing and the same height. Make it look like a before/after or comparison layout.",
    swap_prompt: str = "This is a side-by-side composite image. I need you to: 1) Take the person's appearance from the RIGHT side image, 2) Apply that person's appearance to the person on the LEFT side, 3) Keep the LEFT side background, pose, and scene exactly as they are, 4) Only change the person's appearance, not the environment, 5) Return ONLY the left side image with the updated person. The result should be the left side scene with the right side person's appearance."
):
    """
    Process images through the staged merge pipeline
    
    - **background_image**: The background/scene image
    - **person_image**: The person source image
    - **add_person_prompt**: Prompt for adding person to background
    - **composite_prompt**: Prompt for creating side-by-side composite
    - **swap_prompt**: Prompt for swapping person appearance
    """
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        session_dir = f"output/{session_id}"
        os.makedirs(session_dir, exist_ok=True)
        
        # Save uploaded files
        background_path = f"{session_dir}/background.jpg"
        person_path = f"{session_dir}/person.jpg"
        
        with open(background_path, "wb") as buffer:
            shutil.copyfileobj(background_image.file, buffer)
        
        with open(person_path, "wb") as buffer:
            shutil.copyfileobj(person_image.file, buffer)
        
        logger.info(f"Processing session {session_id}")
        
        # Process images using staged merge service
        results = staged_merge_service.staged_merge_with_kontext(
            image_a_path=background_path,
            image_b_path=person_path,
            add_person_prompt=add_person_prompt,
            composite_prompt=composite_prompt,
            swap_prompt=swap_prompt
        )
        
        # Return file paths and session info
        return {
            "session_id": session_id,
            "status": "completed",
            "results": {
                "person_added": results.get('person_added', ''),
                "composite": results.get('composite', ''),
                "final_swap": results.get('final_swap', '')
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/download/{session_id}/{file_type}")
async def download_result(session_id: str, file_type: str):
    """
    Download a specific result file from a processing session
    
    - **session_id**: The session ID from processing
    - **file_type**: Type of file to download (person_added, composite, final_swap)
    """
    try:
        # Validate file type
        valid_types = ["person_added", "composite", "final_swap"]
        if file_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid file type. Must be one of: {valid_types}")
        
        # Construct file path
        file_path = f"output/{session_id}/{file_type}.jpg"
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_type}")
        
        return FileResponse(
            path=file_path,
            filename=f"{file_type}_{session_id}.jpg",
            media_type="image/jpeg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
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
        
        # Check which files exist
        files = {}
        for file_type in ["person_added", "composite", "final_swap"]:
            file_path = f"{session_dir}/{file_type}.jpg"
            files[file_type] = os.path.exists(file_path)
        
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
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
