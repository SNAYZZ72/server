"""
API models for request/response validation using Pydantic
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import uuid

class WebtoonRequest(BaseModel):
    """Request model for generating a webtoon"""
    prompt: str = Field(..., description="Main prompt describing the manga/webtoon to create")
    style: str = Field(default="manga", description="Art style (manga, webtoon, comic)")
    num_panels: int = Field(default=6, description="Number of panels to generate", ge=1, le=20)
    characters: Optional[List[str]] = Field(default=None, description="List of characters to include")
    additional_context: Optional[str] = Field(default=None, description="Additional context or requirements")

class TaskResponse(BaseModel):
    """Response model for task creation"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class TaskStatus(BaseModel):
    """Response model for task status"""
    task_id: str
    status: str = Field(..., description="Status of the task: pending, processing, completed, failed")
    progress: float = Field(default=0.0, description="Progress from 0.0 to 1.0", ge=0.0, le=1.0)
    result: Optional[Dict[str, Any]] = Field(default=None, description="Results when task is completed")

class PanelUpdate(BaseModel):
    """Request model for updating a panel"""
    description: Optional[str] = Field(default=None, description="Updated visual description")
    characters: Optional[List[str]] = Field(default=None, description="Updated characters list")
    dialogue: Optional[List[Dict[str, str]]] = Field(default=None, description="Updated dialogue")
    size: Optional[str] = Field(default=None, description="Panel size (full, half, third)")
    caption: Optional[str] = Field(default=None, description="Panel caption text")
    style: Optional[str] = Field(default=None, description="Art style for regeneration")

class ImageGenerationRequest(BaseModel):
    """Request model for standalone image generation"""
    prompt: str = Field(..., description="Prompt for the image")
    style: str = Field(default="manga", description="Art style (manga, webtoon, comic)")
    width: int = Field(default=768, description="Image width in pixels")
    height: int = Field(default=1024, description="Image height in pixels")

class ImageGenerationResponse(BaseModel):
    """Response model for image generation"""
    image_path: str = Field(..., description="Path to the generated image")