"""
AI Chat system for SketchDojo - handles conversations and tool execution
"""
import logging
import json
import os
from typing import Dict, List, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.ai import AI
from core.manga_generator import MangaGenerator
from models.panel import PanelRequest

logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    """Chat message model"""
    role: Literal["system", "user", "assistant", "function"] = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")
    name: Optional[str] = Field(None, description="Name of the function (only for function role)")
    tool_call_id: Optional[str] = Field(None, description="ID of the tool call (only for function role)")
    function_call: Optional[Dict[str, Any]] = Field(None, description="Function call details")

class ChatRequest(BaseModel):
    """Chat request model"""
    messages: List[ChatMessage] = Field(..., description="Chat history")
    project_id: str = Field(..., description="ID of the project")

class ChatResponse(BaseModel):
    """Chat response model"""
    message: ChatMessage = Field(..., description="Response message")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls to execute")

class ChatAI:
    """
    AI Chat system for SketchDojo that handles conversations and can execute tools
    """
    
    def __init__(self, ai_client: AI):
        """
        Initialize the ChatAI with an AI client
        
        Args:
            ai_client: Instance of the AI class for model interactions
        """
        self.ai = ai_client
        self.manga_generator = MangaGenerator(ai_client)
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """
        Load the system prompt for the AI chat
        
        Returns:
            System prompt as string
        """
        # Identity section - who the AI is
        identity = """
You are SketchDojo AI, a powerful AI assistant specializing in manga and webtoon creation. You operate within the innovative SketchDojo platform, enabling users to create professional-quality manga/webtoon from text descriptions. You can work both independently and collaboratively with users to bring their creative visions to life.

You are now conversing with a user who wants to create or modify manga/webtoon content. Your purpose is to help them transform their ideas and descriptions into compelling visual narratives using the SketchDojo platform's capabilities.
"""

        # Purpose section - what the AI should do
        purpose = """
Currently, a user has approached you with a creative manga/webtoon task or question. You should analyze their request to determine the best way to assist them.

You should first decide whether specific SketchDojo tools (like panel generation, character creation, etc.) are required to complete their request, or if you can respond directly with advice, examples, or recommendations. Then, set your approach accordingly.

Based on the user's request, either prepare to utilize appropriate creative tools or formulate a helpful response that guides them in their manga creation journey.
"""

        # Tools section - what tools are available
        tools = """
You have access to various manga creation tools to help fulfill the user's requirements.

Available tools:
- generate_story: Generate a complete story based on the user's prompt
- generate_panels: Generate panels based on the story
- generate_image: Generate an image for a specific panel or description
- modify_panel: Modify an existing panel with new details
- generate_webtoon: Generate the complete HTML webtoon using the story and panels

When a user asks you to create a webtoon, manga, or comic, you should follow these steps:
1. First use generate_story to create a compelling narrative
2. Then use generate_panels to design the visual panels
3. Finally use generate_webtoon to produce the complete HTML webtoon that the user can view

You should try to guide the user through this process, asking for details when needed, and then use the tools in sequence to create their webtoon.
"""

        # Guidelines section - how the AI should respond
        guidelines = """
When discussing manga/webtoon creation techniques or suggesting edits, be specific and clear. Use visual descriptions that help the user imagine the result.

Format your response in markdown to enhance readability, especially when providing step-by-step instructions.

When suggesting panel descriptions, be detailed about:
- Character positioning and expressions
- Background elements and atmosphere
- Lighting and visual effects
- Text placement and speech bubbles

Be respectful of different manga styles and preferences. Avoid being judgmental about genres or artistic choices.

Focus on helping users develop their own unique stories and art rather than recreating existing copyrighted works.

Provide specific, actionable suggestions that improve narrative flow and visual impact.
"""
        
        return f"{identity}\n\n{purpose}\n\n{tools}\n\n{guidelines}"
    
    async def process_chat(self, chat_request: ChatRequest) -> ChatResponse:
        """
        Process a chat request and generate a response
        
        Args:
            chat_request: The chat request containing messages and project ID
            
        Returns:
            ChatResponse with assistant's message and any tool calls
        """
        # Prepare messages for the AI
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add user messages from the request
        for msg in chat_request.messages:
            messages.append(msg.dict(exclude_none=True))
        
        # Define available tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_story",
                    "description": "Generate a complete story based on the user's prompt",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The user's prompt for the story"
                            },
                            "style": {
                                "type": "string",
                                "description": "Art style (manga, webtoon, comic)",
                                "default": "manga"
                            }
                        },
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_panels",
                    "description": "Generate manga panels based on the story",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "story": {
                                "type": "object",
                                "description": "The story object to generate panels for"
                            },
                            "num_panels": {
                                "type": "integer",
                                "description": "Number of panels to generate",
                                "default": 6
                            }
                        },
                        "required": ["story"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Generate an image for a specific panel or description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Visual description of what to draw"
                            },
                            "style": {
                                "type": "string",
                                "description": "Art style (manga, webtoon, comic)",
                                "default": "manga"
                            }
                        },
                        "required": ["description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "modify_panel",
                    "description": "Modify an existing panel with new details",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "panel_id": {
                                "type": "string",
                                "description": "ID of the panel to modify"
                            },
                            "description": {
                                "type": "string",
                                "description": "New visual description"
                            },
                            "characters": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "Updated characters in the panel"
                            }
                        },
                        "required": ["panel_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_webtoon",
                    "description": "Generate a complete HTML webtoon based on story and panels",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Main prompt describing the webtoon to create"
                            },
                            "style": {
                                "type": "string",
                                "description": "Art style (manga, webtoon, comic)",
                                "default": "manga"
                            },
                            "num_panels": {
                                "type": "integer",
                                "description": "Number of panels to generate",
                                "default": 6
                            },
                            "additional_context": {
                                "type": "string",
                                "description": "Additional context or requirements for the webtoon"
                            }
                        },
                        "required": ["prompt"]
                    }
                }
            }
        ]
        
        try:
            # Get AI response with potential tool calls
            response = await self.ai.client.chat.completions.create(
                model=self.ai.model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=self.ai.temperature
            )
            
            assistant_message = response.choices[0].message
            content = assistant_message.content or ""
            
            # Check if the AI wants to use tools
            tool_calls = []
            if assistant_message.tool_calls:
                tool_calls = [
                    {
                        "id": tool.id,
                        "name": tool.function.name,
                        "arguments": json.loads(tool.function.arguments)
                    }
                    for tool in assistant_message.tool_calls
                ]
            
            # Create the response message
            response_message = ChatMessage(
                role="assistant",
                content=content,
                function_call=None  # No direct function calls in the new format
            )
            
            return ChatResponse(
                message=response_message,
                tool_calls=tool_calls if tool_calls else None
            )
            
        except Exception as e:
            logger.error(f"Error in chat processing: {str(e)}")
            # Return a graceful error response
            return ChatResponse(
                message=ChatMessage(
                    role="assistant",
                    content=f"I'm sorry, I encountered an error while processing your request. Please try again."
                ),
                tool_calls=None
            )
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool based on the name and arguments
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool
            
        Returns:
            Result of the tool execution as a string
        """
        try:
            if tool_name == "generate_story":
                story = await self.manga_generator.generate_story(
                    arguments.get("prompt", ""),
                    arguments.get("additional_context", None)
                )
                return json.dumps(story)
                
            elif tool_name == "generate_panels":
                story = arguments.get("story", {})
                num_panels = arguments.get("num_panels", 6)
                panels = await self.manga_generator.generate_panels(
                    story,
                    num_panels
                )
                return json.dumps(panels)
                
            elif tool_name == "generate_image":
                # This would actually call the image generation service
                # For now we'll return a placeholder
                return json.dumps({
                    "message": "Image generation started",
                    "description": arguments.get("description", ""),
                    "style": arguments.get("style", "manga")
                })
                
            elif tool_name == "modify_panel":
                # This would actually modify a panel
                # For now we'll return a placeholder
                return json.dumps({
                    "message": "Panel modification started",
                    "panel_id": arguments.get("panel_id", ""),
                    "description": arguments.get("description", "")
                })
                
            elif tool_name == "generate_webtoon":
                # Call the existing webtoon generation API
                from fastapi import BackgroundTasks
                from api.models import WebtoonRequest, TaskResponse
                from api.routes import generate_webtoon_task, tasks
                
                # Create a request for the webtoon generator
                webtoon_request = WebtoonRequest(
                    prompt=arguments.get("prompt", ""),
                    style=arguments.get("style", "manga"),
                    num_panels=arguments.get("num_panels", 6),
                    additional_context=arguments.get("additional_context", "")
                )
                
                # Generate a task ID
                import uuid
                task_id = str(uuid.uuid4())
                
                # Start the webtoon generation process (this is normally done in the API route)
                import asyncio
                asyncio.create_task(generate_webtoon_task(task_id, webtoon_request, self.ai))
                
                # Return the task ID and information
                return json.dumps({
                    "task_id": task_id,
                    "message": "Webtoon generation started",
                    "prompt": arguments.get("prompt", ""),
                    "style": arguments.get("style", "manga"),
                    "num_panels": arguments.get("num_panels", 6),
                    "html_content": "Your webtoon is being generated. It will be displayed once ready."
                })
            
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return json.dumps({"error": f"Error executing {tool_name}: {str(e)}"})
