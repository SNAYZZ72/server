"""
Prompt handling module for managing and processing user prompts
"""
from typing import Dict, Any, Optional, List

class Prompt:
    """
    Class for handling and processing user prompts for manga/webtoon generation
    """
    
    def __init__(
        self, 
        text: str,
        style: str = "manga",
        num_panels: int = 6,
        characters: Optional[List[str]] = None,
        additional_context: Optional[str] = None
    ):
        """
        Initialize a prompt object
        
        Args:
            text: The main prompt text
            style: The desired art style (manga, webtoon, comic, etc.)
            num_panels: The desired number of panels
            characters: Optional list of character names/descriptions
            additional_context: Optional additional context or requirements
        """
        self.text = text
        self.style = style
        self.num_panels = num_panels
        self.characters = characters or []
        self.additional_context = additional_context
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the prompt to a dictionary
        
        Returns:
            Dictionary representation of the prompt
        """
        return {
            "text": self.text,
            "style": self.style,
            "num_panels": self.num_panels,
            "characters": self.characters,
            "additional_context": self.additional_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prompt':
        """
        Create a prompt from a dictionary
        
        Args:
            data: Dictionary with prompt data
            
        Returns:
            Prompt object
        """
        return cls(
            text=data.get("prompt", ""),
            style=data.get("style", "manga"),
            num_panels=data.get("num_panels", 6),
            characters=data.get("characters"),
            additional_context=data.get("additional_context")
        )
    
    def enrich_prompt(self) -> str:
        """
        Enrich the prompt with style information
        
        Returns:
            Enriched prompt string
        """
        enriched = f"{self.text}"
        
        # Add style information
        if self.style.lower() == "manga":
            enriched += " Create a manga-style story with black and white panels, dynamic compositions, and expressive characters."
        elif self.style.lower() == "webtoon":
            enriched += " Create a vertical-scrolling webtoon with colorful panels, clear layouts, and modern character designs."
        elif self.style.lower() == "comic":
            enriched += " Create a comic book style story with bold outlines, action-packed panels, and traditional comic formatting."
        
        # Add character information if provided
        if self.characters:
            enriched += f" The story should include these characters: {', '.join(self.characters)}."
        
        # Add additional context if provided
        if self.additional_context:
            enriched += f" {self.additional_context}"
        
        return enriched