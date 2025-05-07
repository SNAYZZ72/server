"""
Helper utilities for SketchDojo Server
"""
import os
import json
import logging
import base64
import aiofiles
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

def ensure_directories_exist():
    """
    Ensure all required directories exist
    """
    directories = [
        "static/images",
        "static/output",
        "static/temp",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")

def generate_timestamp():
    """
    Generate a timestamp string for filenames
    
    Returns:
        str: Timestamp string in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def save_data_to_json(data: Any, filename: str):
    """
    Save data to a JSON file
    
    Args:
        data: Data to save
        filename: Filename to save to
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving data to {filename}: {str(e)}")

async def save_data_to_json_async(data: Any, filename: str):
    """
    Save data to a JSON file asynchronously
    
    Args:
        data: Data to save
        filename: Filename to save to
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(json_str)
        logger.info(f"Data saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving data to {filename}: {str(e)}")

def load_data_from_json(filename: str) -> Dict[str, Any]:
    """
    Load data from a JSON file
    
    Args:
        filename: Filename to load from
        
    Returns:
        Dictionary with loaded data
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Data loaded from {filename}")
        return data
    except Exception as e:
        logger.error(f"Error loading data from {filename}: {str(e)}")
        return {}

async def load_data_from_json_async(filename: str) -> Dict[str, Any]:
    """
    Load data from a JSON file asynchronously
    
    Args:
        filename: Filename to load from
        
    Returns:
        Dictionary with loaded data
    """
    try:
        async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
            content = await f.read()
        data = json.loads(content)
        logger.info(f"Data loaded from {filename}")
        return data
    except Exception as e:
        logger.error(f"Error loading data from {filename}: {str(e)}")
        return {}

def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image to base64
    
    Args:
        image_path: Path to the image
        
    Returns:
        Base64 encoded string
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string
    except Exception as e:
        logger.error(f"Error encoding image to base64: {str(e)}")
        return ""

async def encode_image_to_base64_async(image_path: str) -> str:
    """
    Encode an image to base64 asynchronously
    
    Args:
        image_path: Path to the image
        
    Returns:
        Base64 encoded string
    """
    try:
        async with aiofiles.open(image_path, "rb") as image_file:
            image_data = await image_file.read()
        encoded_string = base64.b64encode(image_data).decode("utf-8")
        return encoded_string
    except Exception as e:
        logger.error(f"Error encoding image to base64: {str(e)}")
        return ""

def decode_base64_to_image(base64_string: str, output_path: str) -> bool:
    """
    Decode a base64 string to an image
    
    Args:
        base64_string: Base64 encoded image string
        output_path: Path to save the image
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Remove data URL prefix if present
        if "," in base64_string:
            base64_string = base64_string.split(",", 1)[1]
            
        image_data = base64.b64decode(base64_string)
        with open(output_path, "wb") as f:
            f.write(image_data)
        logger.info(f"Image saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error decoding base64 to image: {str(e)}")
        return False

async def decode_base64_to_image_async(base64_string: str, output_path: str) -> bool:
    """
    Decode a base64 string to an image asynchronously
    
    Args:
        base64_string: Base64 encoded image string
        output_path: Path to save the image
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Remove data URL prefix if present
        if "," in base64_string:
            base64_string = base64_string.split(",", 1)[1]
            
        image_data = base64.b64decode(base64_string)
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(image_data)
        logger.info(f"Image saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error decoding base64 to image: {str(e)}")
        return False

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to ensure it's valid
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Ensure filename is not too long
    if len(filename) > 255:
        ext = Path(filename).suffix
        filename = filename[:255-len(ext)] + ext
        
    return filename

def setup_logging(log_file: str = "sketchdojo_server.log", level=logging.INFO):
    """
    Set up logging configuration
    
    Args:
        log_file: Path to the log file
        level: Logging level
    """
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Full path to log file
    log_path = os.path.join("logs", log_file)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path),
        ],
    )
    
    # Reduce logging level for some verbose libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    logger.info(f"Logging configured at level {level} to {log_path}")