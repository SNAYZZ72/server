#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source server/venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p server/static/images
mkdir -p server/static/output
mkdir -p server/static/temp

# Start the FastAPI server
echo "Starting SketchDojo Server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000