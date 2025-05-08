"""
HTML renderer module for generating the final webtoon HTML output
"""
import os
import logging
from typing import List, Dict, Any, Optional
from models.panel import Panel
from models.speech_bubble import SpeechBubble

# Configure logging
logger = logging.getLogger(__name__)

class HTMLRenderer:
    """
    Renders panels and speech bubbles into HTML format for webtoon display
    """
    
    def __init__(self):
        """Initialize the HTML renderer"""
        self.template_dir = os.path.join(os.path.dirname(__file__), "../templates")
        logger.info("HTMLRenderer initialized")
        
    def render_webtoon(
        self, 
        panels: List[Panel], 
        title: str = "SketchDojo Webtoon", 
        timestamp: Optional[str] = None
    ) -> str:
        """
        Render a complete webtoon from panels into HTML
        
        Args:
            panels: List of Panel objects to render
            title: Title of the webtoon
            timestamp: Optional timestamp for the webtoon
            
        Returns:
            HTML string of the complete webtoon
        """
        logger.info(f"Rendering webtoon HTML with {len(panels)} panels")
        
        html = self._get_html_header(title)
        
        # Add story container
        html += '<div class="webtoon-container">\n'
        
        # Add title section
        html += f'''<div class="webtoon-title">
    <h1>{title}</h1>
</div>\n'''
        
        # Render each panel
        panel_content = ""
        for panel in panels:
            panel_content += self._render_panel(panel)
        
        html += panel_content
        
        # Close story container
        html += '</div>\n'
        
        # Add footer
        footer_timestamp = timestamp or ""
        html += self._get_html_footer(footer_timestamp)
        
        logger.info("HTML rendering completed")
        return html
    
    def _render_panel(self, panel: Panel) -> str:
        """
        Render a single panel to HTML
        
        Args:
            panel: Panel object to render
            
        Returns:
            HTML string for the panel
        """
        # Determine panel class based on panel size
        panel_size = getattr(panel, 'size', 'full')
        panel_class = f"panel panel-{panel_size}"
        
        html = f'<div id="panel-{panel.panel_id}" class="{panel_class}">\n'
        
        # Add panel image
        image_path = getattr(panel, 'image_path', None)
        if image_path:
            # Don't add leading slash if it's a full URL
            if image_path.startswith('http://') or image_path.startswith('https://'):
                image_url = image_path
            else:
                # For relative paths, add a leading slash if it doesn't have one
                image_url = f"/{image_path}" if not image_path.startswith('/') else image_path
                
            html += f'  <div class="panel-image"><img src="{image_url}" alt="Panel {panel.panel_id}"></div>\n'
        
        # Add speech bubbles
        speech_bubbles = getattr(panel, 'speech_bubbles', [])
        if speech_bubbles:
            html += self._render_speech_bubbles(panel)
        
        # Add caption if any
        caption = getattr(panel, 'caption', None)
        if caption:
            html += f'  <div class="caption">{caption}</div>\n'
        
        # Add sound effects if any
        effects = getattr(panel, 'effects', [])
        if effects:
            html += self._render_effects(effects)
        
        html += '</div>\n'
        return html
    
    def _render_speech_bubbles(self, panel: Panel) -> str:
        """
        Render speech bubbles for a panel
        
        Args:
            panel: Panel containing speech bubbles
            
        Returns:
            HTML string for speech bubbles
        """
        html = ""
        
        # If panel has structured speech bubble objects
        speech_bubbles = getattr(panel, 'speech_bubbles', [])
        if speech_bubbles:
            for bubble in speech_bubbles:
                style = getattr(bubble, 'style', 'normal')
                bubble_class = f"speech-bubble {style}"
                
                # Get position information
                position = getattr(bubble, 'position', 'top-left')
                position_style = self._get_position_style(bubble)
                
                # Get character
                character = getattr(bubble, 'character', 'Character')
                
                # Get text
                text = getattr(bubble, 'text', '')
                
                # Get tail direction
                tail_direction = getattr(bubble, 'tail_direction', 'bottom')
                
                html += f'  <div class="{bubble_class}" style="{position_style}" data-character="{character}">\n'
                html += f'    <div class="speech-content">{text}</div>\n'
                html += f'    <div class="speech-tail speech-tail-{tail_direction}"></div>\n'
                html += '  </div>\n'
        
        # If panel just has dialogue list without structured bubbles
        elif hasattr(panel, 'dialogue') and panel.dialogue:
            dialogue = panel.dialogue
            for i, dialogue_item in enumerate(dialogue):
                if isinstance(dialogue_item, dict) and 'text' in dialogue_item and 'character' in dialogue_item:
                    character = dialogue_item['character']
                    text = dialogue_item['text']
                else:
                    # Simple string dialogue
                    character = f"character-{i+1}"
                    text = str(dialogue_item)
                
                # Simple top-to-bottom layout
                top_position = 10 + (i * 20)
                left_position = 10 + (i * 5)
                position_style = f"top: {top_position}%; left: {left_position}%;"
                
                html += f'  <div class="speech-bubble" style="{position_style}" data-character="{character}">\n'
                html += f'    <div class="speech-content">{text}</div>\n'
                html += '    <div class="speech-tail speech-tail-bottom"></div>\n'
                html += '  </div>\n'
        
        return html
    
    def _render_effects(self, effects: List[Dict[str, Any]]) -> str:
        """
        Render special effects for a panel
        
        Args:
            effects: List of effect dictionaries
            
        Returns:
            HTML string for effects
        """
        html = ""
        
        for effect in effects:
            if isinstance(effect, str):
                # Simple string effect
                html += f'  <div class="sound-effect" style="top: 50%; left: 50%;">{effect}</div>\n'
            elif isinstance(effect, dict):
                # Dictionary with position and text
                text = effect.get('text', '')
                
                # Get position
                top = effect.get('top', '50%')
                left = effect.get('left', '50%')
                
                # Get style
                style_dict = effect.get('style', {})
                style_str = '; '.join([f"{k}: {v}" for k, v in style_dict.items()])
                
                html += f'  <div class="sound-effect" style="top: {top}; left: {left}; {style_str}">{text}</div>\n'
        
        return html
    
    def _get_position_style(self, bubble: SpeechBubble) -> str:
        """
        Generate CSS positioning style for a speech bubble
        
        Args:
            bubble: SpeechBubble object with position information
            
        Returns:
            CSS style string
        """
        position_style = ""
        
        position = getattr(bubble, 'position', None)
        if position:
            # Handle different position formats
            if isinstance(position, dict):
                for prop, value in position.items():
                    position_style += f"{prop}: {value};"
            elif isinstance(position, str):
                # Handle position as a string like "top-left"
                position_parts = position.split('-')
                
                if "top" in position_parts:
                    position_style += "top: 10%;"
                if "bottom" in position_parts:
                    position_style += "bottom: 10%;"
                if "left" in position_parts:
                    position_style += "left: 10%;"
                if "right" in position_parts:
                    position_style += "right: 10%;"
                if "center" in position_parts:
                    if "top" in position_parts or "bottom" in position_parts:
                        position_style += "left: 50%; transform: translateX(-50%);"
                    else:
                        position_style += "top: 50%; transform: translateY(-50%);"
                        
                # If just "center", center both horizontally and vertically
                if position == "center":
                    position_style = "top: 50%; left: 50%; transform: translate(-50%, -50%);"
        
        return position_style
    
    def _get_html_header(self, title: str) -> str:
        """Get the HTML header with CSS styles"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        /* Reset and base styles */
        body, html {{
            margin: 0;
            padding: 0;
            font-family: 'Comic Sans MS', 'Lato', Arial, sans-serif;
            background-color: #f0f0f0;
        }}
        
        /* Container for the webtoon */
        .webtoon-container {{
            max-width: 800px;
            margin: 0 auto;
            background: black; /* Change to black like typical webtoons */
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            position: relative;
            padding: 0; /* Remove padding */
            font-size: 0; /* Remove any space between inline elements */
            line-height: 0; /* Remove any space between lines */
        }}
        
        /* Webtoon title styles */
        .webtoon-title {{
            padding: 15px 0;
            text-align: center;
            background: #000;
            color: white;
            font-size: 16px; /* Reset font size for this element */
            line-height: 1.4; /* Reset line height for this element */
        }}
        
        .webtoon-title h1 {{
            margin: 0;
            font-size: 28px;
            font-family: 'Arial', sans-serif;
        }}
        
        /* Panel styles */
        .panel {{
            position: relative;
            margin: 0;
            padding: 0;
            overflow: hidden;
            display: block;
        }}
        
        .panel-full {{
            width: 100%;
        }}
        
        .panel-half {{
            width: 50%;
            display: inline-block;
        }}
        
        .panel-third {{
            width: 33.333%;
            display: inline-block;
        }}
        
        .panel-image {{
            width: 100%;
        }}
        
        .panel-image img {{
            width: 100%;
            display: block;
        }}
        
        /* Speech bubble styles */
        .speech-bubble {{
            position: absolute;
            background: white;
            border-radius: 20px;
            padding: 10px 15px;
            max-width: 40%;
            box-shadow: 0 0 5px rgba(0,0,0,0.2);
            z-index: 2;
            font-size: 16px; /* Reset font-size */
            line-height: 1.4; /* Reset line-height */
            font-family: 'Comic Sans MS', 'Lato', Arial, sans-serif; /* Reset font */
        }}
        
        .speech-content {{
            font-size: 1rem;
            line-height: 1.4;
        }}
        
        .speech-tail {{
            position: absolute;
            width: 20px;
            height: 20px;
            background: white;
            transform: rotate(45deg);
            box-shadow: 0 0 5px rgba(0,0,0,0.2);
            z-index: 1;
        }}
        
        .speech-tail-left {{
            left: -5px;
            top: 50%;
            margin-top: -10px;
        }}
        
        .speech-tail-right {{
            right: -5px;
            top: 50%;
            margin-top: -10px;
        }}
        
        .speech-tail-top {{
            top: -5px;
            left: 50%;
            margin-left: -10px;
        }}
        
        .speech-tail-bottom {{
            bottom: -5px;
            left: 50%;
            margin-left: -10px;
        }}
        
        /* Speech bubble styles */
        .speech-bubble.thought {{
            border-radius: 30px;
            background: white;
            border: 2px dashed #ccc;
        }}
        
        .speech-bubble.shout {{
            background: #ffffcc;
            border: 2px solid #ffcc00;
            font-weight: bold;
        }}
        
        .speech-bubble.whisper {{
            background: #f0f0f0;
            color: #666;
            font-style: italic;
        }}
        
        /* Caption styles */
        .caption {{
            font-style: italic;
            text-align: center;
            padding: 0.5rem;
            background: rgba(0,0,0,0.7);
            color: white;
            position: absolute;
            bottom: 0;
            width: 100%;
            box-sizing: border-box;
            font-size: 14px; /* Reset font size */
            line-height: 1.4; /* Reset line height */
            font-family: 'Comic Sans MS', 'Lato', Arial, sans-serif; /* Reset font */
        }}
        
        /* Footer styles */
        .webtoon-footer {{
            padding: 20px;
            text-align: center;
            font-size: 14px;
            line-height: 1.4;
            color: #999;
            background: #000;
            font-family: 'Arial', sans-serif;
        }}
        
        /* Sound effect styles */
        .sound-effect {{
            position: absolute;
            font-family: 'Impact', sans-serif;
            color: #ff6600;
            font-weight: bold;
            font-size: 24px;
            text-shadow: 2px 2px 0 white, -2px -2px 0 white, 2px -2px 0 white, -2px 2px 0 white;
            transform: rotate(-15deg);
            z-index: 3;
        }}
        
        /* Character name tag */
        .character-name {{
            position: absolute;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 2;
        }}
        
        /* Different panel borders */
        .panel-normal {{
            border: 1px solid #ccc;
        }}
        
        .panel-flashback {{
            border: 2px dashed #999;
        }}
        
        .panel-dream {{
            border: 3px wavy #9966cc;
        }}
        
        /* Responsive design */
        @media (max-width: 600px) {{
            .panel-half, .panel-third {{
                width: 100%;
                display: block;
            }}
            
            .speech-bubble {{
                max-width: 60%;
            }}
        }}
    </style>
</head>
<body>
"""

    def _get_html_footer(self, timestamp: str) -> str:
        """Get the HTML footer with timestamp"""
        return f"""
    <div class="webtoon-footer">
        <p>Created with SketchDojo - {timestamp}</p>
    </div>
</body>
</html>
"""