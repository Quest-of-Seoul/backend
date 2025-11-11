"""
Quest of Seoul - AI Service Backend
FastAPI backend for AI features (VLM, Docent, TTS)
"""

from dotenv import load_dotenv
import os
import logging

# Load environment variables FIRST (before importing routers)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import docent, vlm

app = FastAPI(
    title="Quest of Seoul AI Service",
    description="AI Service API for VLM Image Analysis, AI Docent, and TTS",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "VLM",
            "description": "Vision-Language Model for image analysis and landmark recognition"
        },
        {
            "name": "AI Docent",
            "description": "AI-powered conversational tour guide"
        }
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include AI routers only
app.include_router(vlm.router, prefix="/vlm", tags=["VLM"])
app.include_router(docent.router, prefix="/docent", tags=["AI Docent"])

@app.on_event("startup")
async def startup_event():
    logger.info("Quest of Seoul AI Service starting up...")
    logger.info("Available endpoints: /docs, /redoc")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Quest of Seoul AI Service shutting down...")

@app.get("/")
async def root():
    return {
        "message": "Quest of Seoul AI Service",
        "version": "2.0.0",
        "status": "active",
        "services": [
            "VLM Image Analysis",
            "AI Docent",
            "TTS"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "vlm": "active",
            "docent": "active",
            "tts": "active"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
