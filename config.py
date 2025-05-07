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

# Call verification on import
verify_env_vars()