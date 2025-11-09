"""
Quest of Seoul - FastAPI Backend
Main application entry point
"""

from dotenv import load_dotenv
import os

# Load environment variables FIRST (before importing routers)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import docent, quest, reward, vlm

app = FastAPI(
    title="Quest of Seoul API",
    description="AI AR Docent App Backend",
    version="1.0.0"
)

# CORS middleware - allow React Native app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(docent.router, prefix="/docent", tags=["Docent"])
app.include_router(quest.router, prefix="/quest", tags=["Quest"])
app.include_router(reward.router, prefix="/reward", tags=["Reward"])
app.include_router(vlm.router, prefix="/vlm", tags=["VLM - Image Analysis"])

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
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
