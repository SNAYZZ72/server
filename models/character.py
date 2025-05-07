"""
Character data model for manga/webtoon characters
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class Character(BaseModel):
    """
    Represents a character in a manga or webtoon
    """
    name: str
    description: Optional[str] = None
    appearance: Optional[Dict[str, Any]] = None
    personality: Optional[Dict[str, Any]] = None
    relationships: Optional[Dict[str, str]] = None
    
    # Character expressions for consistent rendering
    expressions: Optional[Dict[str, str]] = None
    
    class Config:
        arbitrary_types_allowed = True
        
class CharacterRequest(BaseModel):
    """
    Request model for creating a character
    """
    name: str
    description: str
    appearance: Optional[Dict[str, Any]] = None
    personality_traits: Optional[List[str]] = None