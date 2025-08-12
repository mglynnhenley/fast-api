# Image Processing API

A FastAPI-based service for staged image merging and person swapping using AI-powered image editing.

## Features

- **Staged Image Processing**: Multi-step pipeline for adding and swapping people in images
- **AI-Powered Editing**: Uses Black Forest API for intelligent image manipulation
- **Side-by-Side Composites**: Manual image compositing without AI calls
- **Session Management**: Track and manage processing sessions
- **File Downloads**: Download processed images via API endpoints

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health information

### Image Processing
- `POST /process-images` - Process images through the staged merge pipeline
- `GET /download/{session_id}/{file_type}` - Download processed images
- `GET /sessions/{session_id}` - Get session information
- `DELETE /sessions/{session_id}` - Delete a session

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

## Local Development

### Prerequisites
- Python 3.11+
- Black Forest API key

### Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables:
   ```bash
   export BFL_API_KEY="your_api_key_here"
   ```
4. Run the development server:
   ```bash
   python app.py
   ```
   Or with uvicorn:
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

### Testing
Run the test script to verify endpoints:
```bash
python test_api.py
```

## Railway Deployment

### Prerequisites
- Railway account
- GitHub repository with your code

### Deployment Steps

1. **Connect to Railway**:
   - Go to [Railway](https://railway.app)
   - Connect your GitHub repository
   - Create a new project

2. **Configure Environment Variables**:
   - Add `BFL_API_KEY` with your Black Forest API key
   - Railway will automatically set `PORT` environment variable

3. **Deploy**:
   - Railway will automatically detect the FastAPI app
   - The `Procfile` tells Railway how to run the application
   - Deployment happens automatically on git push

4. **Verify Deployment**:
   - Check the Railway dashboard for deployment status
   - Visit your Railway URL to see the API running
   - Access `/docs` for interactive API documentation

### Railway Configuration Files

- **Procfile**: Tells Railway how to run the app
- **runtime.txt**: Specifies Python version
- **requirements.txt**: Lists all dependencies
- **.gitignore**: Excludes unnecessary files

## API Usage Examples

### Process Images
```bash
curl -X POST "https://your-railway-url.railway.app/process-images" \
  -F "background_image=@background.jpg" \
  -F "person_image=@person.jpg" \
  -F "add_person_prompt=Add a person to this scene" \
  -F "composite_prompt=Create side-by-side comparison" \
  -F "swap_prompt=Swap person appearance"
```

### Download Results
```bash
curl -X GET "https://your-railway-url.railway.app/download/{session_id}/final_swap"
```

### Get Session Info
```bash
curl -X GET "https://your-railway-url.railway.app/sessions/{session_id}"
```

## Project Structure

```
fastapihackathon/
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── Procfile              # Railway deployment config
├── runtime.txt           # Python version specification
├── .gitignore           # Git ignore rules
├── test_api.py          # API testing script
├── services/
│   ├── staged_merge_service.py  # Core image processing logic
│   ├── black_forest_api.py      # Black Forest API client
│   └── street_view_service.py   # Street view service
├── input/               # Input images
├── output/              # Generated images (created automatically)
└── uploads/             # Uploaded files (created automatically)
```

## Environment Variables

- `BFL_API_KEY`: Black Forest API key (required)
- `PORT`: Port number (set automatically by Railway)

## Error Handling

The API includes comprehensive error handling:
- File validation
- Session management
- API error responses
- Logging for debugging

## Security Considerations

- CORS is configured for development (configure properly for production)
- File upload validation
- Session-based file management
- Environment variable protection

## Monitoring

- Health check endpoints for monitoring
- Structured logging
- Session tracking
- Error reporting

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review the logs in Railway dashboard
3. Test with the provided test script
