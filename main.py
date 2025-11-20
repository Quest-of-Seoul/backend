"""Quest of Seoul - FastAPI Backend"""

from dotenv import load_dotenv
import os
import logging
from contextlib import asynccontextmanager

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import docent, quest, reward, vlm, recommend

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Quest of Seoul API starting up...")
    
    try:
        from services.db import get_db
        from services.tts import get_tts_client
        from services.pinecone_store import get_pinecone_index
        
        get_db()
        logger.info("Database connection initialized")
        
        get_tts_client()
        logger.info("TTS client initialized")
        
        get_pinecone_index()
        logger.info("Pinecone index initialized")
        
    except Exception as e:
        logger.warning(f"Service initialization warning: {e}")
    
    yield
    
    try:
        from services.cache import get_image_embedding_cache, get_place_cache, get_tts_cache
        
        cache = get_image_embedding_cache()
        removed = cache.cleanup_expired()
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")
    except Exception as e:
        logger.warning(f"Cache cleanup warning: {e}")
    
    logger.info("Quest of Seoul API shutting down...")


app = FastAPI(
    title="Quest of Seoul API",
    description="AI AR Docent App Backend with VLM, Quest, and Reward Management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Docent",
            "description": "AI-powered conversational tour guide with TTS support"
        },
        {
            "name": "Quest",
            "description": "Location-based quest management and progress tracking"
        },
        {
            "name": "Reward",
            "description": "Points and rewards system for user achievements"
        },
        {
            "name": "VLM - Image Analysis",
            "description": "Vision-Language Model for image analysis and landmark recognition"
        },
        {
            "name": "Recommend - Place Recommendation",
            "description": "AI-based place recommendation using image similarity"
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(docent.router, prefix="/docent", tags=["Docent"])
app.include_router(quest.router, prefix="/quest", tags=["Quest"])
app.include_router(reward.router, prefix="/reward", tags=["Reward"])
app.include_router(vlm.router, prefix="/vlm", tags=["VLM - Image Analysis"])
app.include_router(recommend.router, prefix="/recommend", tags=["Recommend - Place Recommendation"])

@app.get("/")
async def root():
    return {
        "message": "Quest of Seoul API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
