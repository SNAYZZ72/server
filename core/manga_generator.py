"""
Core manga generation module that orchestrates the entire manga creation process
"""
import os
import json
import aiofiles
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.ai import AI
from core.html_renderer import HTMLRenderer
from models.panel import Panel
from services.story_service import StoryService
from services.image_service import ImageService
from services.layout_service import LayoutService
from utils.helpers import ensure_directories_exist, generate_timestamp, save_data_to_json
from config import get_image_url

# Configure logging
logger = logging.getLogger(__name__)

class MangaGenerator:
    """
    Main class that orchestrates the manga/webtoon generation process
    """
    
    def __init__(self, ai: AI = None):
        """
        Initialize services and dependencies
        
        Args:
            ai: Optional AI instance. If not provided, a new one will be created.
        """
        self.ai = ai or AI()
        self.story_service = StoryService(self.ai)
        self.image_service = ImageService(self.ai)
        self.layout_service = LayoutService()
        self.html_renderer = HTMLRenderer()
        
        # Ensure output directories exist
        ensure_directories_exist()
        
        logger.info("MangaGenerator initialized")
        
    async def generate_story(self, prompt: str, additional_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a story outline from the prompt
        
        Args:
            prompt: The main user prompt
            additional_context: Optional additional context or requirements
            
        Returns:
            A dictionary containing the generated story elements
        """
        logger.info("Generating story from prompt")
        story = await self.story_service.generate_story(prompt, additional_context)
        
        # Add a timestamp to track generation time
        story["generated_at"] = generate_timestamp()
        
        logger.info("Story generation completed")
        return story
        
    async def generate_panels(self, story: Dict[str, Any], num_panels: int) -> List[Panel]:
        """
        Generate panel descriptions from the story
        
        Args:
            story: The story outline dictionary
            num_panels: The desired number of panels
            
        Returns:
            A list of Panel objects
        """
        logger.info(f"Generating {num_panels} panels from story")
        panels = await self.story_service.generate_panels(story, num_panels)
        
        # Apply layout considerations to each panel
        logger.info("Applying layout to panels")
        for panel in panels:
            await self.layout_service.apply_layout(panel)
            
        return panels
    
    async def generate_image_for_panel(self, panel: Panel, style: str) -> str:
        """
        Generate an image for a specific panel
        
        Args:
            panel: The Panel object to generate an image for
            style: The desired art style (manga, webtoon, etc.)
            
        Returns:
            The URL to the generated image (accessible from anywhere)
        """
        logger.info(f"Generating image for panel {panel.panel_id}")
        
        try:
            # Image service now returns both file_path and url
            file_path, image_url = await self.image_service.generate_image(
                panel.description,
                panel.characters,
                style,
                f"panel_{panel.panel_id}"
            )
            
            # Store the accessible URL in the panel's image_path
            # This ensures it's accessible from anywhere
            panel.image_path = image_url
            
            logger.info(f"Image generated at {file_path} (URL: {image_url})")
            return image_url
            
        except Exception as e:
            logger.error(f"Error generating image for panel {panel.panel_id}: {str(e)}")
            # Use a placeholder image if generation fails
            placeholder_path = "static/images/placeholder.jpg"
            placeholder_url = get_image_url(placeholder_path)
            panel.image_path = placeholder_url
            return placeholder_url
        
    async def generate_html_output(self, panels: List[Panel], task_id: str) -> str:
        """
        Generate the final HTML output for the manga/webtoon
        
        Args:
            panels: List of Panel objects
            task_id: Unique task identifier
            
        Returns:
            Path to the generated HTML file
        """
        # Create a unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webtoon_{task_id}_{timestamp}.html"
        output_path = f"static/output/{filename}"
        
        logger.info(f"Generating HTML output at {output_path}")
        
        # Generate HTML content
        html_content = self.html_renderer.render_webtoon(
            panels, 
            title=f"SketchDojo Webtoon #{task_id}",
            timestamp=timestamp
        )
        
        # Save HTML file asynchronously
        try:
            async with aiofiles.open(output_path, "w") as f:
                await f.write(html_content)
                
            # Save panel data for reference
            data_path = f"static/output/data_{task_id}_{timestamp}.json"
            panel_data = [panel.dict() for panel in panels]
            
            await save_data_to_json_async(data_path, panel_data)
                
            logger.info(f"HTML output saved to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error saving HTML output: {str(e)}")
            raise
        
    async def update_panel(self, panel_id: str, updates: Dict[str, Any]) -> Panel:
        """
        Update a specific panel with new details
        
        Args:
            panel_id: ID of the panel to update
            updates: Dictionary of updates to apply
            
        Returns:
            Updated Panel object
        """
        logger.info(f"Updating panel {panel_id}")
        
        # This would retrieve the panel from storage and update it
        # Placeholder implementation
        panel = Panel(
            panel_id=panel_id,
            description=updates.get("description", "Updated panel"),
            characters=updates.get("characters", []),
            dialogue=updates.get("dialogue", [])
        )
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(panel, key):
                setattr(panel, key, value)
                
        # Regenerate image if needed
        if "description" in updates or "characters" in updates:
            await self.generate_image_for_panel(panel, updates.get("style", "manga"))
            
        logger.info(f"Panel {panel_id} updated")
        return panel

async def save_data_to_json_async(filename: str, data: Any):
    """
    Save data to a JSON file asynchronously
    
    Args:
        filename: Path to save the file
        data: Data to save
    """
    try:
        json_str = json.dumps(data, indent=2)
        async with aiofiles.open(filename, "w") as f:
            await f.write(json_str)
        logger.info(f"Data saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving data to {filename}: {str(e)}")