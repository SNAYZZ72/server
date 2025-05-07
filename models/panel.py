"""
Panel data model for representing manga/webtoon panels
"""
from typing import List, Dict, Any, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, validator

from models.speech_bubble import SpeechBubble

class Panel(BaseModel):
    """
    Represents a single panel in a manga or webtoon
    """
    panel_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str = Field(..., description="Visual description of what should be drawn")
    characters: List[str] = Field(default_factory=list, description="Characters present in the panel")
    dialogue: List[Any] = Field(default_factory=list, description="Dialogue lines in the panel")
    speech_bubbles: List[SpeechBubble] = Field(default_factory=list, description="Speech bubbles with positioning")
    size: str = Field(default="full", description="Panel size (full, half, third)")
    image_path: Optional[str] = Field(default=None, description="Path to the panel's image")
    caption: Optional[str] = Field(default=None, description="Optional caption text for the panel")
    position: Optional[Dict[str, Any]] = Field(default=None, description="Panel positioning data")
    effects: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Special effects in the panel")
    
    @validator('size')
    def validate_size(cls, v):
        """Validate the panel size is one of the allowed values"""
        allowed = ['full', 'half', 'third', 'quarter']
        if v not in allowed:
            raise ValueError(f'Size must be one of {allowed}')
        return v
    
    def dict(self, *args, **kwargs):
        """Custom dict method to handle nested models"""
        result = super().dict(*args, **kwargs)
        if 'speech_bubbles' in result and result['speech_bubbles']:
            result['speech_bubbles'] = [
                sb if isinstance(sb, dict) else sb.dict(*args, **kwargs) 
                for sb in result['speech_bubbles']
            ]
        return result

class PanelRequest(BaseModel):
    """
    Request model for creating or updating a panel
    """
    description: str = Field(..., description="Visual description of what should be drawn")
    characters: List[str] = Field(default_factory=list, description="Characters to include in the panel")
    dialogue: List[str] = Field(default_factory=list, description="Dialogue lines for the panel")
    size: str = Field(default="full", description="Panel size (full, half, third)")
    caption: Optional[str] = Field(default=None, description="Caption text for the panel")
    style: str = Field(default="manga", description="Art style for the panel")
    position: Optional[Dict[str, Any]] = Field(default=None, description="Panel positioning data")
    
    @validator('size')
    def validate_size(cls, v):
        """Validate the panel size is one of the allowed values"""
        allowed = ['full', 'half', 'third', 'quarter']
        if v not in allowed:
            raise ValueError(f'Size must be one of {allowed}')
        return v
    
    @validator('style')
    def validate_style(cls, v):
        """Validate the art style is one of the allowed values"""
        allowed = ['manga', 'webtoon', 'comic', 'sketch', 'realistic']
        if v not in allowed:
            raise ValueError(f'Style must be one of {allowed}')
        return v