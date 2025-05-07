"""
Speech bubble data model for representing dialogue in manga/webtoon panels
"""
from typing import Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, validator

class SpeechBubble(BaseModel):
    """
    Represents a speech bubble in a manga or webtoon panel
    """
    text: str = Field(..., description="Content text of the speech bubble")
    character: str = Field(..., description="Character speaking the dialogue")
    position: Union[Dict[str, str], str] = Field(
        ..., 
        description="Position of the bubble (e.g., 'top-left' or {'top': '10%', 'left': '20%'})"
    )
    style: str = Field(
        default="normal", 
        description="Bubble style: normal, thought, shout, whisper"
    )
    tail_direction: str = Field(
        default="bottom", 
        description="Direction of the speech tail: top, right, bottom, left"
    )
    size: str = Field(
        default="medium", 
        description="Size of the bubble: small, medium, large"
    )
    font_style: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Custom font styling"
    )
    
    @validator('style')
    def validate_style(cls, v):
        """Validate the bubble style is one of the allowed values"""
        allowed = ['normal', 'thought', 'shout', 'whisper']
        if v not in allowed:
            raise ValueError(f'Style must be one of {allowed}')
        return v
    
    @validator('tail_direction')
    def validate_tail_direction(cls, v):
        """Validate the tail direction is one of the allowed values"""
        allowed = ['top', 'right', 'bottom', 'left', 'none']
        if v not in allowed:
            raise ValueError(f'Tail direction must be one of {allowed}')
        return v
    
    @validator('size')
    def validate_size(cls, v):
        """Validate the bubble size is one of the allowed values"""
        allowed = ['small', 'medium', 'large']
        if v not in allowed:
            raise ValueError(f'Size must be one of {allowed}')
        return v
    
    @validator('position')
    def validate_position(cls, v):
        """Validate the position is in an acceptable format"""
        if isinstance(v, str):
            # Check if position string follows expected format (e.g., 'top-left')
            position_parts = v.split('-')
            if len(position_parts) > 2:
                raise ValueError('String position should be in format "vertical-horizontal" (e.g., "top-left")')
            
            # Validate vertical part
            if len(position_parts) > 0:
                vertical = position_parts[0]
                if vertical not in ['top', 'center', 'bottom'] and vertical != 'center':
                    raise ValueError('Vertical position must be "top", "center", or "bottom"')
            
            # Validate horizontal part if present
            if len(position_parts) > 1:
                horizontal = position_parts[1]
                if horizontal not in ['left', 'center', 'right']:
                    raise ValueError('Horizontal position must be "left", "center", or "right"')
        
        return v

class SpeechBubbleUpdate(BaseModel):
    """Request model for updating a speech bubble"""
    text: Optional[str] = None
    character: Optional[str] = None
    position: Optional[Union[Dict[str, str], str]] = None
    style: Optional[str] = None
    tail_direction: Optional[str] = None
    size: Optional[str] = None
    font_style: Optional[Dict[str, Any]] = None