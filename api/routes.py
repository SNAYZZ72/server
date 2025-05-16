"""
API routes for manga/webtoon generation
"""
import logging
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Body, Depends
from fastapi.responses import HTMLResponse, FileResponse

from api.models import (
    WebtoonRequest,
    TaskResponse,
    TaskStatus,
    ProjectRequest,
    ProjectResponse
)
from core.ai import AI
from core.manga_generator import MangaGenerator
from models.panel import PanelRequest

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory task storage (use a database in production)
tasks = {}
projects = {}

async def get_ai_client() -> AI:
    """Dependency to get AI client instance"""
    return AI(
        model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7")),
    )

async def generate_webtoon_task(
    task_id: str, 
    request: WebtoonRequest,
    ai: AI
):
    """Background task to generate a webtoon"""
    try:
        # Update task status to processing
        tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="processing",
            progress=0.0
        )
        
        logger.info(f"Starting generation for task {task_id}")
        
        # Initialize the manga generator with AI client
        generator = MangaGenerator(ai)
        
        # Generate the story and update progress
        tasks[task_id].progress = 0.1
        logger.info(f"Generating story for task {task_id}")
        
        story = await generator.generate_story(
            request.prompt, 
            request.additional_context
        )
        tasks[task_id].progress = 0.3
        
        # Generate panels and update progress
        logger.info(f"Generating panels for task {task_id}")
        panels = await generator.generate_panels(
            story, 
            request.num_panels
        )
        tasks[task_id].progress = 0.5
        
        # Generate images for each panel
        logger.info(f"Generating images for task {task_id}")
        for i, panel in enumerate(panels):
            await generator.generate_image_for_panel(
                panel, 
                request.style
            )
            tasks[task_id].progress = 0.5 + ((i + 1) / len(panels) * 0.4)
        
        # Generate HTML output
        logger.info(f"Generating HTML output for task {task_id}")
        html_path = await generator.generate_html_output(panels, task_id)
        
        # Update task status to completed
        tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="completed",
            progress=1.0,
            result={
                "html_path": html_path,
                "panel_count": len(panels),
                "story_title": story.get("title", "Untitled Webtoon")
            }
        )
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}", exc_info=True)
        # Update task status to failed
        tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="failed",
            progress=0.0,
            result={"error": str(e)}
        )

@router.post("/generate", response_model=TaskResponse)
async def generate_webtoon(
    background_tasks: BackgroundTasks,
    request: WebtoonRequest,
    ai: AI = Depends(get_ai_client)
):
    """Start a new webtoon generation task"""
    task_id = str(uuid.uuid4())
    logger.info(f"Creating new generation task: {task_id}")
    
    # Store initial task status
    tasks[task_id] = TaskStatus(
        task_id=task_id,
        status="pending", 
        progress=0.0
    )
    
    # Add generation task to background tasks
    background_tasks.add_task(
        generate_webtoon_task, 
        task_id, 
        request,
        ai
    )
    
    return TaskResponse(task_id=task_id)

@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a task"""
    if task_id not in tasks:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    
    logger.debug(f"Retrieved status for task {task_id}: {tasks[task_id].status}")
    return tasks[task_id]

@router.get("/result/{task_id}", response_class=HTMLResponse)
async def get_webtoon_result(task_id: str):
    """Get the HTML result of a completed webtoon generation task"""
    if task_id not in tasks:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    if task.status != "completed":
        logger.warning(f"Task {task_id} is not completed: {task.status}")
        raise HTTPException(status_code=400, detail=f"Task is not completed, current status: {task.status}")
    
    html_path = task.result.get("html_path")
    if not html_path or not os.path.exists(html_path):
        logger.error(f"HTML output not found for task {task_id}: {html_path}")
        raise HTTPException(status_code=404, detail="HTML output not found")
    
    with open(html_path, "r") as f:
        html_content = f.read()
    
    logger.info(f"Returning HTML result for task {task_id}")
    return HTMLResponse(content=html_content)

@router.post("/projects", response_model=ProjectResponse)
async def create_project(request: ProjectRequest):
    """Create a new project with an initial prompt"""
    try:
        project_id = str(uuid.uuid4())
        logger.info(f"Creating new project: {project_id}")
        
        # Store initial project data
        projects[project_id] = {
            "id": project_id,
            "name": f"Webtoon Project {project_id[:8]}",  # Generate a random name
            "prompt": request.prompt,
            "created_at": datetime.now().isoformat(),
            "status": "created"
        }
        
        logger.info(f"Project {project_id} created successfully")
        return ProjectResponse(
            projectId=project_id,
            projectName=projects[project_id]["name"]
        )
        
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result/{task_id}/download", response_class=FileResponse)
async def download_webtoon_result(task_id: str):
    """Download the HTML result of a completed webtoon generation task"""
    if task_id not in tasks:
        logger.warning(f"Task not found: {task_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    if task.status != "completed":
        logger.warning(f"Task {task_id} is not completed: {task.status}")
        raise HTTPException(status_code=400, detail=f"Task is not completed, current status: {task.status}")
    
    html_path = task.result.get("html_path")
    if not html_path or not os.path.exists(html_path):
        logger.error(f"HTML output not found for task {task_id}: {html_path}")
        raise HTTPException(status_code=404, detail="HTML output not found")
    
    logger.info(f"Returning downloadable HTML for task {task_id}")
    return FileResponse(
        path=html_path, 
        filename=f"webtoon_{task_id}.html", 
        media_type="text/html"
    )

@router.post("/panels", response_model=TaskResponse)
async def create_custom_panel(
    background_tasks: BackgroundTasks,
    request: PanelRequest = Body(...),
    ai: AI = Depends(get_ai_client)
):
    """Create a custom panel with specific details"""
    task_id = str(uuid.uuid4())
    logger.info(f"Creating custom panel task: {task_id}")
    
    # Store initial task status
    tasks[task_id] = TaskStatus(
        task_id=task_id,
        status="pending", 
        progress=0.0
    )
    
    # TODO: Implement custom panel creation logic
    # This would be a simplified version of the webtoon generation
    # focused on creating a single panel
    
    return TaskResponse(task_id=task_id)