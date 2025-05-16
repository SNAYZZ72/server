"""
Chat API routes for the SketchDojo platform
"""
import logging
import uuid
import json
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, Body, HTTPException
from pydantic import BaseModel, Field

from core.ai import AI
from core.chat_ai import ChatAI, ChatMessage, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory chat history storage (use a database in production)
chat_history = {}

# Store HTML preview content for each project
html_preview_content = {}

class ToolCallRequest(BaseModel):
    """Request for executing a tool call"""
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: Dict[str, Any] = Field(..., description="Arguments for the tool call")
    project_id: str = Field(..., description="ID of the project")
    message_id: Optional[str] = Field(None, description="ID of the message containing the tool call")

class ToolCallResponse(BaseModel):
    """Response from executing a tool call"""
    result: Dict[str, Any] = Field(..., description="Result of executing the tool")
    message: str = Field(..., description="Human-readable message about the execution")

async def get_chat_ai() -> ChatAI:
    """Dependency to get a ChatAI instance"""
    ai_client = AI(
        model_name="gpt-4o-mini",  # Use the same model as in the main AI module
        temperature=0.7
    )
    return ChatAI(ai_client)

@router.post("", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    chat_ai: ChatAI = Depends(get_chat_ai)
):
    """
    Chat with the SketchDojo AI
    
    Args:
        request: The chat request with messages and project ID
        chat_ai: ChatAI instance (injected by FastAPI)
        
    Returns:
        ChatResponse containing the AI's response
    """
    project_id = request.project_id
    
    # Initialize chat history for this project if it doesn't exist
    if project_id not in chat_history:
        chat_history[project_id] = []
    
    # Process the chat request
    try:
        response = await chat_ai.process_chat(request)
        
        # Store the messages in chat history
        chat_history[project_id].extend(request.messages)
        chat_history[project_id].append(response.message)
        
        return response
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@router.post("/tool-call", response_model=ToolCallResponse)
async def execute_tool_call(
    request: ToolCallRequest,
    chat_ai: ChatAI = Depends(get_chat_ai)
):
    """
    Execute a tool call from the AI
    
    Args:
        request: The tool call request with name, arguments, and project ID
        chat_ai: ChatAI instance (injected by FastAPI)
        
    Returns:
        ToolCallResponse with the result of the tool execution
    """
    project_id = request.project_id
    
    try:
        # Execute the tool
        result_str = await chat_ai.execute_tool(request.tool_name, request.arguments)
        result = json.loads(result_str)
        
        # Create a function message for the result
        if request.message_id:
            function_message = ChatMessage(
                role="function",
                content=result_str
            )
            if project_id in chat_history:
                chat_history[project_id].append(function_message)
                
            # Store HTML content if present in the result
            if 'html_content' in result and project_id is not None:
                html_preview_content[project_id] = result['html_content']
        
        # Create a user-friendly message about what happened
        message = f"Successfully executed {request.tool_name}"
        
        return ToolCallResponse(result=result, message=message)
    except Exception as e:
        logger.error(f"Error executing tool {request.tool_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")

class ProjectHistoryResponse(BaseModel):
    """Response model for project history including chat messages and HTML content"""
    messages: List[ChatMessage] = Field(default_factory=list, description="Chat messages history")
    html_content: str = Field(default="", description="HTML preview content")

class StoreHtmlRequest(BaseModel):
    """Request to store HTML content for a project"""
    project_id: str = Field(..., description="ID of the project")
    html_content: str = Field(..., description="HTML content to store")

@router.get("/{project_id}/history", response_model=ProjectHistoryResponse)
async def get_chat_history(project_id: str):
    """
    Get the chat history and HTML preview content for a project
    
    Args:
        project_id: ID of the project
        
    Returns:
        ProjectHistoryResponse containing chat messages and HTML content
    """
    response = ProjectHistoryResponse()
    
    # Get chat messages
    if project_id in chat_history:
        response.messages = chat_history[project_id]
    
    # Get HTML preview content
    if project_id in html_preview_content:
        response.html_content = html_preview_content[project_id]
    
    return response

@router.post("/store-html", response_model=dict)
async def store_html_content(request: StoreHtmlRequest):
    """
    Store HTML content for a project
    
    Args:
        request: The request with project ID and HTML content
        
    Returns:
        Success message
    """
    project_id = request.project_id
    
    # Store the HTML content
    html_preview_content[project_id] = request.html_content
    
    return {"message": "HTML content stored successfully"}
