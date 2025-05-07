"""
AI interface for interacting with language models to generate manga/webtoon content
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, TypeVar, Generic, Literal
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel, Field

from openai import AsyncOpenAI, APIError, RateLimitError

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class StoryResponse(BaseModel):
    """Story generation response schema"""
    setting: Dict[str, str] = Field(..., description="Time period and location details")
    main_characters: List[Dict[str, str]] = Field(..., description="List of main characters with descriptions")
    plot_summary: str = Field(..., description="Summary of the plot")
    key_scenes: List[Union[str, Dict[str, str]]] = Field(..., description="Key scenes for visual panels, can be strings or dictionaries with 'scene' key")
    theme: str = Field(..., description="Theme of the story")
    mood: str = Field(..., description="Overall mood/tone")

class PanelDescription(BaseModel):
    """Panel description schema"""
    visual_description: str = Field(..., description="What should be drawn")
    characters: List[str] = Field(..., description="Characters present in the panel")
    dialogue: List[Dict[str, str]] = Field(default_factory=list, description="Dialogue lines with character names")
    special_effects: Optional[List[str]] = Field(default_factory=list, description="Special effects or text elements")
    panel_size: str = Field(default="full-width", description="Panel size recommendation")

class PanelDescriptionsResponse(BaseModel):
    """Response containing panel descriptions"""
    panels: List[PanelDescription] = Field(..., description="List of panel descriptions")

class SpeechBubble(BaseModel):
    """Speech bubble schema"""
    text: str = Field(..., description="Text content of the speech bubble")
    character: str = Field(..., description="Character speaking")
    position: str = Field(..., description="Position on panel (top-left, center-right, etc.)")
    style: str = Field(default="normal", description="Style (normal, thought, shouted)")
    tail_direction: str = Field(default="bottom", description="Direction the tail points")

class SpeechBubblesResponse(BaseModel):
    """Response containing speech bubbles"""
    speechBubbles: List[SpeechBubble]

class AI:
    """
    Interface for interacting with language models to generate manga/webtoon content.
    
    This class uses the latest OpenAI Python client (≥1.0.0) and provides methods
    to generate various aspects of manga/webtoons such as story elements,
    panel descriptions, character dialogue, and image prompts.
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        organization_id: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize the AI class with model configuration.
        
        Args:
            model_name: Name of the language model to use
            temperature: Temperature setting for generation (higher = more creative)
            api_key: API key for OpenAI (if None, uses environment variable)
            organization_id: Organization ID for OpenAI (if applicable)
            max_retries: Maximum number of retry attempts on API errors
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_retries = max_retries
        
        # Configure client
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required. Set it via the api_key parameter or OPENAI_API_KEY environment variable.")
        
        # Initialize OpenAI client without proxy configuration
        # The error was caused by the client trying to use proxies from environment variables
        self.client = AsyncOpenAI(
            api_key=api_key,
            organization=organization_id,
            # Explicitly set http_client without proxies to avoid the error
            http_client=None
        )
        
        logger.info(f"Initialized AI with model: {model_name}")
    
    @retry(
        retry=retry_if_exception_type((APIError, RateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _make_request(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_model: Optional[type[T]] = None,
        response_format: Optional[Literal["json_object", "text"]] = None,
        temperature: Optional[float] = None,
    ) -> Union[str, T]:
        """
        Make a request to the language model with retry logic.
        
        Args:
            system_prompt: System prompt to guide the model
            user_prompt: User prompt containing the main request
            response_model: Optional Pydantic model for response validation
            response_format: Optional response format specification
            temperature: Optional temperature override
            
        Returns:
            Either a string or a validated Pydantic model based on response_model
        """
        try:
            request_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature or self.temperature,
            }
            
            # Add response format if specified
            if response_format:
                request_params["response_format"] = {"type": response_format}
            
            logger.debug(f"Making request with params: {request_params}")
            
            response = await self.client.chat.completions.create(**request_params)
            content = response.choices[0].message.content
            
            # Validate and convert to Pydantic model if specified
            if response_model and response_format == "json_object":
                try:
                    parsed_content = json.loads(content)
                    
                    # Preprocess StoryResponse to fix common validation issues
                    if response_model == StoryResponse:
                        # Ensure theme field exists
                        if "theme" not in parsed_content:
                            # Try to extract theme from plot summary or setting
                            if "plot_summary" in parsed_content:
                                parsed_content["theme"] = "Themes derived from the plot"
                            elif "setting" in parsed_content and isinstance(parsed_content["setting"], dict) and parsed_content["setting"]:
                                parsed_content["theme"] = "Themes related to the setting"
                            else:
                                parsed_content["theme"] = "Adventure and discovery"
                        
                        # Ensure mood field exists
                        if "mood" not in parsed_content:
                            # Try to infer mood from other fields
                            if "plot_summary" in parsed_content and "tragic" in parsed_content["plot_summary"].lower():
                                parsed_content["mood"] = "Somber and reflective"
                            elif "plot_summary" in parsed_content and ("action" in parsed_content["plot_summary"].lower() or "battle" in parsed_content["plot_summary"].lower()):
                                parsed_content["mood"] = "Intense and dramatic"
                            else:
                                parsed_content["mood"] = "Balanced mix of light and serious moments"
                    
                    # Preprocess panel descriptions to fix common validation issues
                    elif response_model == PanelDescriptionsResponse and "panels" in parsed_content:
                        for panel in parsed_content["panels"]:
                            # Ensure characters field exists and is a list
                            if "characters" not in panel or not isinstance(panel["characters"], list) or not panel["characters"]:
                                # Extract character names from dialogue if possible
                                if "dialogue" in panel and panel["dialogue"]:
                                    if isinstance(panel["dialogue"], str):
                                        # Try to extract character names from dialogue string
                                        dialogue_parts = panel["dialogue"].split(":", 1)
                                        if len(dialogue_parts) > 0:
                                            panel["characters"] = [dialogue_parts[0].strip()]
                                        else:
                                            panel["characters"] = ["Character"]
                                    elif isinstance(panel["dialogue"], list) and panel["dialogue"] and isinstance(panel["dialogue"][0], dict) and "character" in panel["dialogue"][0]:
                                        # Extract character names from dialogue list of dicts
                                        panel["characters"] = list(set([d["character"] for d in panel["dialogue"] if "character" in d]))
                                    else:
                                        panel["characters"] = ["Character"]
                                else:
                                    panel["characters"] = ["Character"]
                            
                            # Ensure dialogue is in the correct format (list of dicts)
                            if "dialogue" in panel:
                                if isinstance(panel["dialogue"], str):
                                    # Handle dialogue as a single string (common format: "Character: Text")
                                    dialogue_text = panel["dialogue"].strip()
                                    dialogue_parts = dialogue_text.split(":", 1)
                                    
                                    if len(dialogue_parts) > 1:
                                        character = dialogue_parts[0].strip()
                                        text = dialogue_parts[1].strip()
                                        panel["dialogue"] = [{"character": character, "text": text}]
                                    else:
                                        # If no character name can be extracted, use a default
                                        panel["dialogue"] = [{"character": "Character", "text": dialogue_text}]
                                elif not isinstance(panel["dialogue"], list):
                                    # Convert any non-list dialogue to a list with a single item
                                    panel["dialogue"] = [{"character": "Character", "text": str(panel["dialogue"])}]
                                elif panel["dialogue"] and isinstance(panel["dialogue"][0], str):
                                    # Convert list of strings to list of dicts
                                    formatted_dialogue = []
                                    for dialogue_line in panel["dialogue"]:
                                        dialogue_parts = dialogue_line.split(":", 1)
                                        if len(dialogue_parts) > 1:
                                            character = dialogue_parts[0].strip()
                                            text = dialogue_parts[1].strip()
                                            formatted_dialogue.append({"character": character, "text": text})
                                        else:
                                            formatted_dialogue.append({"character": "Character", "text": dialogue_line})
                                    panel["dialogue"] = formatted_dialogue
                                
                                # Ensure each dialogue entry has both character and text fields
                                for i, dialogue_entry in enumerate(panel["dialogue"]):
                                    if not isinstance(dialogue_entry, dict):
                                        panel["dialogue"][i] = {"character": "Character", "text": str(dialogue_entry)}
                                    else:
                                        if "character" not in dialogue_entry:
                                            dialogue_entry["character"] = "Character"
                                        if "text" not in dialogue_entry:
                                            dialogue_entry["text"] = "..."
                    
                    # Use model_validate instead of parse_obj (which is deprecated in newer Pydantic versions)
                    return response_model.model_validate(parsed_content)
                except Exception as e:
                    logger.error(f"Error parsing response as {response_model.__name__}: {str(e)}")
                    logger.debug(f"Raw response: {content}")
                    raise ValueError(f"Failed to parse response as {response_model.__name__}: {str(e)}")
            
            return content
            
        except (APIError, RateLimitError) as e:
            logger.warning(f"API error (retrying): {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error making request: {str(e)}")
            raise
    
    async def generate_story(self, prompt: str, additional_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a story outline for the manga/webtoon.
        
        Args:
            prompt: The main prompt describing the desired manga/webtoon
            additional_context: Optional additional context or specifications
            
        Returns:
            A validated StoryResponse object with the generated story elements
        """
        system_message = """
        You are a professional manga/webtoon writer. Your task is to create a compelling 
        story outline based on the provided prompt. The outline should include:
        1. Setting (time period, location)
        2. Main characters (with brief descriptions)
        3. Plot summary
        4. Key scenes that would make good visual panels
        5. Theme and mood
        
        Provide your response as a structured JSON with these elements.
        """
        
        user_message = prompt
        if additional_context:
            user_message += f"\n\nAdditional context: {additional_context}"
        
        try:
            result = await self._make_request(
                system_message,
                user_message,
                response_model=StoryResponse,
                response_format="json_object",
            )
            
            # Normalize key_scenes to handle both string and dictionary formats
            if isinstance(result, BaseModel):
                # Use model_dump instead of dict() (which is deprecated in newer Pydantic versions)
                story_dict = result.model_dump()
                # Convert any scene dictionaries to strings if needed
                if "key_scenes" in story_dict and story_dict["key_scenes"]:
                    normalized_scenes = []
                    for scene in story_dict["key_scenes"]:
                        if isinstance(scene, dict) and "scene" in scene:
                            normalized_scenes.append(scene["scene"])
                        else:
                            normalized_scenes.append(scene)
                    story_dict["key_scenes"] = normalized_scenes
                return story_dict
            return result
            
        except Exception as e:
            logger.error(f"Error generating story: {str(e)}")
            raise
    
    async def generate_panel_descriptions(
        self, 
        story: Dict[str, Any], 
        num_panels: int
    ) -> List[Dict[str, Any]]:
        """
        Generate detailed panel descriptions from the story outline.
        
        Args:
            story: The story outline dictionary
            num_panels: The desired number of panels
            
        Returns:
            A list of validated PanelDescription objects
        """
        system_message = """
        You are a professional manga/webtoon artist and writer. Your task is to create detailed 
        panel descriptions based on the provided story outline. Each panel description should include:
        1. Visual description (what should be drawn)
        2. Characters present
        3. Dialogue (if any)
        4. Special effects or text elements
        5. Panel size recommendation (full-width, half-width, etc.)
        
        Format your response as a JSON object with a "panels" array containing panel objects.
        """
        
        user_message = f"""
        Story outline: {json.dumps(story)}
        
        Create {num_panels} panel descriptions for this story that would make a compelling manga/webtoon.
        Make sure the panels flow logically and capture key moments from the story.
        """
        
        try:
            result = await self._make_request(
                system_message,
                user_message,
                response_model=PanelDescriptionsResponse,
                response_format="json_object"
            )
            
            if isinstance(result, PanelDescriptionsResponse):
                # Use model_dump instead of dict() (which is deprecated in newer Pydantic versions)
                return [panel.model_dump() for panel in result.panels]
            return result
            
        except Exception as e:
            logger.error(f"Error generating panel descriptions: {str(e)}")
            raise
    
    async def generate_image_prompt(
        self, 
        panel_description: str,
        characters: List[str],
        style: str
    ) -> str:
        """
        Generate a detailed image prompt for an image generation model.
        
        Args:
            panel_description: Description of the panel content
            characters: List of characters in the panel
            style: The desired art style (manga, webtoon, etc.)
            
        Returns:
            A detailed prompt for image generation
        """
        system_message = """
        You are a professional manga/webtoon artist. Your task is to create a detailed prompt 
        for an image generation AI based on the panel description provided. The prompt should be 
        detailed and specific, including:
        1. Scene description
        2. Character positions and expressions
        3. Lighting and atmosphere
        4. Art style references
        5. Composition details
        
        The prompt should be detailed yet concise, optimized for image generation AI.
        """
        
        user_message = f"""
        Panel description: {panel_description}
        Characters: {', '.join(characters)}
        Style: {style}
        
        Create a detailed image generation prompt that will result in a high-quality {style}-style illustration.
        """
        
        try:
            result = await self._make_request(
                system_message,
                user_message,
                temperature=0.7
            )
            return result
            
        except Exception as e:
            logger.error(f"Error generating image prompt: {str(e)}")
            raise
    
    async def generate_speech_bubbles(
        self,
        panel_description: str,
        dialogue: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Generate speech bubble placements and styles.
        
        Args:
            panel_description: Description of the panel content
            dialogue: List of dialogue dictionaries with character and text keys
            
        Returns:
            A list of validated SpeechBubble objects
        """
        system_message = """
        You are a professional manga/webtoon editor specializing in text and speech bubble placement.
        Your task is to determine optimal placement and styling for speech bubbles in a panel.
        For each dialogue line, provide:
        1. Position (top-left, center-right, etc.)
        2. Style (normal, thought, shouted, etc.)
        3. Tail direction (pointing to which character)
        
        Format your response as a JSON object with a "speechBubbles" array.
        """
        
        user_message = f"""
        Panel description: {panel_description}
        Dialogue lines: {json.dumps(dialogue)}
        
        Determine the optimal placement and styling for speech bubbles in this panel.
        """
        
        try:
            result = await self._make_request(
                system_message,
                user_message,
                response_model=SpeechBubblesResponse,
                response_format="json_object",
                temperature=0.5,
            )
            
            if isinstance(result, SpeechBubblesResponse):
                # Use model_dump instead of dict() (which is deprecated in newer Pydantic versions)
                return [bubble.model_dump() for bubble in result.speechBubbles]
            return result
            
        except Exception as e:
            logger.error(f"Error generating speech bubbles: {str(e)}")
            raise