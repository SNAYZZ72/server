"""
Main entry point for the FastAPI server for manga/webtoon generation
"""
import os
from typing import Dict, Any, Optional

# Import config to load environment variables
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.routes import router as api_router

app = FastAPI(title="SketchDojo API", description="API for generating manga/webtoons from prompts", debug=True)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for images and output
os.makedirs("static/output", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(api_router, prefix="/api")

# Task storage (in memory for simplicity, use a database in production)
tasks = {}

class TaskStatus(BaseModel):
    status: str
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    return {"message": "Welcome to SketchDojo API"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)