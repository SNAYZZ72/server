"""
Story service module for generating manga/webtoon stories and panel content
"""
import uuid
import logging
from typing import Dict, List, Any, Optional

from core.ai import AI
from models.panel import Panel
from models.speech_bubble import SpeechBubble

# Configure logging
logger = logging.getLogger(__name__)

class StoryService:
    """
    Service for generating story elements and panel content
    """
    
    def __init__(self, ai: AI):
        """
        Initialize the story service
        
        Args:
            ai: AI interface for generation tasks
        """
        self.ai = ai
        logger.info("StoryService initialized")
    
    async def generate_story(self, prompt: str, additional_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a story outline from a prompt
        
        Args:
            prompt: User prompt for the manga/webtoon
            additional_context: Optional additional context or requirements
            
        Returns:
            Dictionary with story elements
        """
        logger.info("Generating story from prompt")
        
        try:
            story = await self.ai.generate_story(prompt, additional_context)
            
            # Add title if not present
            if "title" not in story:
                # Extract a title from the prompt or theme
                if "theme" in story:
                    story["title"] = story["theme"].title()
                else:
                    # Get first 5 words of prompt as title
                    title_words = prompt.split()[:5]
                    story["title"] = " ".join(title_words).title()
            
            logger.info(f"Story generated with title: {story.get('title', 'Untitled')}")
            return story
            
        except Exception as e:
            logger.error(f"Error generating story: {str(e)}")
            raise
    
    async def generate_panels(self, story: Dict[str, Any], num_panels: int) -> List[Panel]:
        """
        Generate panel descriptions from a story outline
        
        Args:
            story: Story outline dictionary
            num_panels: Number of panels to generate
            
        Returns:
            List of Panel objects
        """
        logger.info(f"Generating {num_panels} panels")
        
        try:
            # Generate panel descriptions using AI
            panel_descriptions = await self.ai.generate_panel_descriptions(story, num_panels)
            
            panels = []
            for i, panel_desc in enumerate(panel_descriptions):
                # Create a unique ID for the panel
                panel_id = str(uuid.uuid4())
                
                # Extract panel information
                description = panel_desc.get("visual_description", "")
                characters = panel_desc.get("characters", [])
                
                # Process dialogue
                dialogue = panel_desc.get("dialogue", [])
                speech_bubbles = []
                
                # If dialogue is provided, create speech bubbles
                if dialogue:
                    # If dialogue is a list of strings, convert to dict format
                    if isinstance(dialogue, list) and dialogue and isinstance(dialogue[0], str):
                        dialogue = [{"character": "Character", "text": text} for text in dialogue]
                    
                    # If dialogue is a dict with character keys, convert to list
                    if isinstance(dialogue, dict):
                        dialogue = [{"character": char, "text": text} for char, text in dialogue.items()]
                    
                    # Generate speech bubbles from dialogue
                    if dialogue:
                        try:
                            speech_bubbles_data = await self.ai.generate_speech_bubbles(description, dialogue)
                            
                            # Create SpeechBubble objects
                            for bubble_data in speech_bubbles_data:
                                speech_bubbles.append(SpeechBubble(
                                    text=bubble_data.get("text", ""),
                                    character=bubble_data.get("character", "Unknown"),
                                    position=bubble_data.get("position", "top-left"),
                                    style=bubble_data.get("style", "normal"),
                                    tail_direction=bubble_data.get("tail_direction", "bottom")
                                ))
                        except Exception as bubble_error:
                            logger.error(f"Error generating speech bubbles: {str(bubble_error)}")
                            # Create basic speech bubbles if AI generation fails
                            for j, d in enumerate(dialogue):
                                speech_bubbles.append(SpeechBubble(
                                    text=d.get("text", ""),
                                    character=d.get("character", "Character"),
                                    position=f"{'top' if j % 2 == 0 else 'bottom'}-{'left' if j % 2 == 0 else 'right'}",
                                    style="normal",
                                    tail_direction="bottom"
                                ))
                
                # Create the panel object
                panel = Panel(
                    panel_id=panel_id,
                    description=description,
                    characters=characters,
                    dialogue=dialogue,
                    speech_bubbles=speech_bubbles,
                    size=panel_desc.get("panel_size", "full"),
                    caption=panel_desc.get("caption", None),
                    effects=panel_desc.get("special_effects", [])
                )
                
                panels.append(panel)
                logger.debug(f"Created panel {panel_id}: {description[:50]}...")
            
            logger.info(f"Generated {len(panels)} panels successfully")
            return panels
            
        except Exception as e:
            logger.error(f"Error generating panels: {str(e)}")
            raise
    
    async def generate_dialogue(self, panel_description: str, characters: List[str]) -> List[Dict[str, str]]:
        """
        Generate dialogue for characters in a panel
        
        Args:
            panel_description: Description of the panel
            characters: List of characters in the panel
            
        Returns:
            List of dialogue entries with character and text
        """
        logger.info(f"Generating dialogue for panel with {len(characters)} characters")
        
        try:
            # This is a placeholder implementation
            # In a real implementation, this would use the AI to generate dialogue
            if not characters:
                return []
                
            dialogue = []
            for i, character in enumerate(characters[:2]):  # Limit to 2 characters for simplicity
                dialogue.append({
                    "character": character,
                    "text": f"This is placeholder dialogue for {character}."
                })
                
            return dialogue
            
        except Exception as e:
            logger.error(f"Error generating dialogue: {str(e)}")
            return []