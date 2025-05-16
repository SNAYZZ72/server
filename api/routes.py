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
        
        # Add retry logic with a maximum number of attempts
        max_attempts = 3
        attempt = 0
        story = None
        
        while attempt < max_attempts:
            try:
                attempt += 1
                story = await generator.generate_story(
                    request.prompt, 
                    request.additional_context
                )
                # If successful, break out of the retry loop
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{max_attempts} failed: {str(e)}")
                if attempt >= max_attempts:
                    raise ValueError(f"Failed to generate story after {max_attempts} attempts: {str(e)}")
                # Wait briefly before retry
                await asyncio.sleep(1)
        
        tasks[task_id].progress = 0.3
        
        # Generate panels and update progress with similar retry logic
        logger.info(f"Generating panels for task {task_id}")
        attempt = 0
        panels = None
        
        while attempt < max_attempts:
            try:
                attempt += 1
                panels = await generator.generate_panels(
                    story, 
                    request.num_panels
                )
                break
            except Exception as e:
                logger.warning(f"Panel generation attempt {attempt}/{max_attempts} failed: {str(e)}")
                if attempt >= max_attempts:
                    raise ValueError(f"Failed to generate panels after {max_attempts} attempts: {str(e)}")
                await asyncio.sleep(1)
                
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
        
        # Generate a basic fallback HTML when validation fails
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error Generating Webtoon</title>
            <style>
                body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }}
                .error-container {{ background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 20px; margin: 20px 0; }}
                h1 {{ color: #721c24; }}
                .message {{ background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; }}
                .suggestion {{ background: #d1ecf1; padding: 15px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>Oops! There was a problem generating your webtoon</h1>
            <div class="error-container">
                <p>We encountered an error while creating your webtoon based on the prompt:</p>
                <div class="message"><strong>"{request.prompt}"</strong></div>
            </div>
            <div class="suggestion">
                <h3>Try one of these instead:</h3>
                <ul>
                    <li>"Create a simple manga about a student discovering magic powers"</li>
                    <li>"Generate a short comic about a detective solving a mystery"</li>
                    <li>"Make a fantasy webtoon with a hero and a dragon"</li>
                </ul>
            </div>
            <p>Technical details: {str(e)[:150]}...</p>
        </body>
        </html>
        """
        
        # Save the fallback HTML
        fallback_html_path = f"static/webtoons/{task_id}.html"
        os.makedirs(os.path.dirname(fallback_html_path), exist_ok=True)
        with open(fallback_html_path, "w") as f:
            f.write(html_content)
            
        # Update task status to failed but provide the fallback HTML
        tasks[task_id] = TaskStatus(
            task_id=task_id,
            status="failed",
            progress=0.0,
            result={
                "error": str(e),
                "html_path": fallback_html_path,
                "fallback": True
            }
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