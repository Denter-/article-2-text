"""
Python AI Worker - FastAPI Service
Handles AI-powered site learning and complex extractions
"""
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from app.database import Database
from app.ai_worker import AIWorker

# Configure logging
logging.basicConfig(
    level=settings.log_level.upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Article Extraction AI Worker",
    description="AI-powered site learning and complex article extraction",
    version="1.0.0"
)

# Initialize database and worker
db = Database(settings.database_url)
ai_worker = None


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global ai_worker
    db.connect()
    ai_worker = AIWorker(db)
    logger.info("AI Worker service started")


@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    db.close()
    logger.info("AI Worker service stopped")


# Request/Response models
class LearnRequest(BaseModel):
    job_id: str
    url: str
    

class LearnResponse(BaseModel):
    success: bool
    message: str
    config: Optional[dict] = None
    error: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-worker",
        "gemini_enabled": ai_worker.site_registry.use_gemini if ai_worker else False
    }


@app.post("/learn", response_model=LearnResponse)
async def learn_site(request: LearnRequest):
    """
    Learn extraction rules for a new site using AI
    This endpoint is called when no config exists for a domain
    """
    logger.info(f"Received learning request for job {request.job_id}: {request.url}")
    
    try:
        result = ai_worker.process_learning_job(request.job_id, request.url)
        
        if result['success']:
            return LearnResponse(
                success=True,
                message="Site learned and article extracted successfully",
                config=result.get('config')
            )
        else:
            return LearnResponse(
                success=False,
                message="Failed to learn site",
                error=result.get('error')
            )
    
    except Exception as e:
        logger.error(f"Error processing learning request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-browser")
async def extract_with_browser(request: LearnRequest):
    """
    Extract article using browser for JavaScript-rendered sites
    """
    logger.info(f"Browser extraction for job {request.job_id}: {request.url}")
    
    try:
        # This would use Playwright for JS-heavy sites
        # For now, treat same as learning
        result = ai_worker.process_learning_job(request.job_id, request.url)
        
        return LearnResponse(
            success=result['success'],
            message="Browser extraction completed" if result['success'] else "Extraction failed",
            error=result.get('error')
        )
    
    except Exception as e:
        logger.error(f"Error in browser extraction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8081,
        reload=False,
        log_level=settings.log_level.lower()
    )

