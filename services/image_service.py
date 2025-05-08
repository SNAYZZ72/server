"""
Image service module for generating manga/webtoon panel images
"""
import os
import base64
import aiohttp
import aiofiles
import logging
from typing import List, Optional, Tuple
from datetime import datetime

from core.ai import AI
from utils.helpers import ensure_directories_exist
from config import IMAGES_PATH, get_image_url

# Configure logging
logger = logging.getLogger(__name__)

class ImageService:
    """
    Service for generating panel images using AI image generation
    """
    
    def __init__(self, ai: AI):
        """
        Initialize the image service
        
        Args:
            ai: AI interface for generation tasks
        """
        self.ai = ai
        # Try to get API key from multiple possible environment variable names
        self.api_key = os.getenv("STABILITY_API_KEY") or os.getenv("STABLE_DIFFUSION_API_KEY")
        self.image_api_url = os.getenv(
            "IMAGE_API_URL", 
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        )
        
        # Log API key status
        if self.api_key:
            logger.info("Stable Diffusion API key found, image generation will be enabled")
            api_key_masked = self.api_key[:6] + "..." + self.api_key[-4:] if len(self.api_key) > 10 else "***"
            logger.debug(f"Using API key: {api_key_masked}")
        else:
            logger.warning("No Stable Diffusion API key found, will use placeholder images")
        
        # Create images directory if it doesn't exist
        ensure_directories_exist()
        logger.info("ImageService initialized")
    
    async def generate_image(
        self, 
        panel_description: str,
        characters: List[str],
        style: str,
        filename_prefix: str
    ) -> Tuple[str, str]:
        """
        Generate an image for a panel
        
        Args:
            panel_description: Description of the panel content
            characters: List of characters in the panel
            style: Art style for the image (manga, webtoon, etc.)
            filename_prefix: Prefix for the generated image filename
            
        Returns:
            Tuple containing (file_system_path, accessible_url) for the generated image
        """
        logger.info(f"Generating image for panel: {filename_prefix}")
        
        try:
            # Generate a detailed prompt for the image generator
            image_prompt = await self.ai.generate_image_prompt(
                panel_description, 
                characters, 
                style
            )
            logger.debug(f"Generated image prompt: {image_prompt[:100]}...")
            
            # Generate the image
            image_path, image_url = await self._call_image_api(image_prompt, style, filename_prefix)
            logger.info(f"Image generated at: {image_path} (URL: {image_url})")
            
            return image_path, image_url
        
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            # Return a placeholder image path
            placeholder_path = await self._generate_placeholder_image(filename_prefix)
            return placeholder_path
    
    async def _call_image_api(
        self, 
        prompt: str, 
        style: str,
        filename_prefix: str
    ) -> Tuple[str, str]:
        """
        Call the image generation API
        
        Args:
            prompt: Detailed prompt for image generation
            style: Art style for the image
            filename_prefix: Prefix for the generated image filename
            
        Returns:
            Tuple containing (file_system_path, accessible_url) for the generated image
        """
        # Modify prompt based on style
        style_prefix = ""
        if style.lower() == "manga":
            style_prefix = "Manga style, black and white, detailed linework, "
        elif style.lower() == "webtoon":
            style_prefix = "Webtoon style, vibrant colors, clean linework, "
        elif style.lower() == "comic":
            style_prefix = "Comic book style, strong outlines, flat colors, "
        
        full_prompt = style_prefix + prompt
        logger.debug(f"Full image prompt: {full_prompt[:100]}...")
        
        # Check if we have the API key for Stability AI
        if not self.api_key:
            logger.warning("No Stability API key found, using placeholder image")
            return await self._generate_placeholder_image(filename_prefix)
        
        # Log that we're attempting to generate an image with Stable Diffusion
        logger.info("Using Stable Diffusion API to generate image")
        
        # Call Stability AI API for image generation
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Truncate prompt to avoid API error (max 2000 chars)
            truncated_prompt = full_prompt[:1950] if len(full_prompt) > 1950 else full_prompt
            if len(full_prompt) > 1950:
                logger.warning(f"Prompt was truncated from {len(full_prompt)} to 1950 characters")
            
            # Use valid dimensions for SDXL v1.0
            # Valid pairs: 1024x1024, 1152x896, 1216x832, 1344x768, 1536x640, 640x1536, 768x1344, 832x1216, 896x1152
            payload = {
                "text_prompts": [
                    {"text": truncated_prompt, "weight": 1.0}
                ],
                "cfg_scale": 7,
                # Use standard square dimensions which work well for manga panels
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30,
            }
            
            logger.debug("Calling Stability AI API")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.image_api_url, 
                    json=payload, 
                    headers=headers
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Process the generated image
                        if "artifacts" in response_data and len(response_data["artifacts"]) > 0:
                            # Get the first generated image
                            image_data = response_data["artifacts"][0]["base64"]
                            
                            # Save the image to disk
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            image_filename = f"{filename_prefix}_{timestamp}.png"
                            image_path = f"{IMAGES_PATH}/{image_filename}"
                            
                            # Decode and save image
                            image_bytes = base64.b64decode(image_data)
                            async with aiofiles.open(image_path, "wb") as f:
                                await f.write(image_bytes)
                            
                            # Generate accessible URL
                            image_url = get_image_url(image_path)
                            
                            logger.info(f"Image saved to {image_path} (URL: {image_url})")
                            return image_path, image_url
                        else:
                            logger.error("No image artifacts returned from API")
                            return await self._generate_placeholder_image(filename_prefix)
                    else:
                        error_text = await response.text()
                        logger.error(f"API error ({response.status}): {error_text}")
                        return await self._generate_placeholder_image(filename_prefix)
        
        except Exception as e:
            logger.error(f"Error calling image API: {str(e)}")
            return await self._generate_placeholder_image(filename_prefix)
    
    async def _generate_placeholder_image(self, filename_prefix: str) -> Tuple[str, str]:
        """
        Generate a placeholder image for development/testing
        
        Args:
            filename_prefix: Prefix for the generated image filename
            
        Returns:
            Tuple containing (file_system_path, accessible_url) for the placeholder image
        """
        # Check if placeholder already exists
        default_placeholder_path = "static/images/default_placeholder.jpg"
        placeholder_path = "static/images/placeholder.jpg"
        
        # If neither placeholder exists, create a very simple one
        if not os.path.exists(placeholder_path) and not os.path.exists(default_placeholder_path):
            from PIL import Image, ImageDraw, ImageFont
            
            logger.info("Creating default placeholder image")
            
            # Create a simple placeholder image
            width, height = 768, 1024
            image = Image.new("RGB", (width, height), color=(240, 240, 240))
            draw = ImageDraw.Draw(image)
            
            # Add placeholder text
            try:
                # Try to load a font
                font = ImageFont.load_default()
                draw.text(
                    (width//2, height//2), 
                    "Placeholder Image", 
                    fill=(0, 0, 0), 
                    font=font, 
                    anchor="mm"
                )
            except Exception:
                # If font loading fails, draw a rectangle
                draw.rectangle(
                    [(width//4, height//4), (width*3//4, height*3//4)], 
                    outline=(0, 0, 0)
                )
            
            # Save the image
            os.makedirs("static/images", exist_ok=True)
            image.save(placeholder_path, "JPEG")
            logger.info(f"Created placeholder image at {placeholder_path}")
        
        # Use existing placeholder
        if os.path.exists(placeholder_path):
            path_to_return = placeholder_path
        elif os.path.exists(default_placeholder_path):
            path_to_return = default_placeholder_path
        else:
            # If all else fails, return the path even if the file doesn't exist
            logger.warning("No placeholder image found, returning path anyway")
            path_to_return = placeholder_path
        
        # Generate accessible URL
        url_to_return = get_image_url(path_to_return)
        logger.info(f"Using placeholder image: {path_to_return} (URL: {url_to_return})")
        
        return path_to_return, url_to_return