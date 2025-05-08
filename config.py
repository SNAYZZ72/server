"""Configuration module for loading environment variables"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify required environment variables
def verify_env_vars():
    """Verify that all required environment variables are set"""
    required_vars = [
        "OPENAI_API_KEY",
        "STABLE_DIFFUSION_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Application configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
STATIC_PATH = "static"
IMAGES_PATH = f"{STATIC_PATH}/images"

# Define URL paths for better accessibility
def get_image_url(relative_path):
    """Convert a relative path to a full URL with the BASE_URL"""
    # If the path already starts with http:// or https://, assume it's already a full URL
    if relative_path.startswith(("http://", "https://")):
        return relative_path
    
    # Remove any leading slashes in the relative path
    if relative_path.startswith("/"):
        relative_path = relative_path[1:]
    
    # Return the full URL
    return f"{BASE_URL}/{relative_path}"

# Call verification on import
verify_env_vars()