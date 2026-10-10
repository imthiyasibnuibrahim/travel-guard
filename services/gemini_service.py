import os
import json
import logging
import re
from typing import Optional

import google.generativeai as genai
from PIL import Image
import io

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_gemini_api_key() -> str:
    """Get the Gemini API key from environment."""
    return os.environ.get("GEMINI_API_KEY", "").strip()


def get_model(vision: bool = False) -> genai.GenerativeModel:
    """Get the Gemini model instance."""
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    return genai.GenerativeModel(
        model_name,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            top_p=0.8,
            max_output_tokens=4096,
        )
    )


def parse_json_response(text: str) -> dict:
    """Safely parse JSON from LLM response, handling markdown code blocks."""
    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1).strip()
    
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON object or array in the text
    for pattern in [r'\{.*\}', r'\[.*\]']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    
    logger.error(f"Failed to parse JSON from response: {text[:200]}")
    return {"error": "Failed to parse AI response", "raw_response": text[:500]}


async def ask_gemini(
    prompt: str,
    image_bytes: Optional[bytes] = None,
    system_instruction: str = ""
) -> dict:
    """Send a prompt to Gemini and parse the JSON response."""
    api_key = get_gemini_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY not set")
        return {"error": "API key not configured"}
    
    try:
        genai.configure(api_key=api_key)
        model = get_model(vision=image_bytes is not None)
        
        parts = []
        
        if system_instruction:
            parts.append(system_instruction + "\n\n")
        
        parts.append(prompt)
        
        if image_bytes:
            image = Image.open(io.BytesIO(image_bytes))
            parts.append(image)
        
        response = model.generate_content(parts)
        
        if response.text:
            return parse_json_response(response.text)
        else:
            return {"error": "Empty response from AI"}
    
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {"error": f"AI service error: {str(e)}"}
