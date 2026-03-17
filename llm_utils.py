"""
Utility functions for LLM providers.
"""

import logging
import asyncio
from typing import Any, Dict, Optional, List
from models import ModelProvider, OllamaProvider, GeminiProvider, GroqProvider, FailoverProvider
from enum import Enum

logger = logging.getLogger(__name__)


# Remove duplicate enum from prompt.py context if needed

class ReasoningIntensity(Enum):
    LOW = "low"
    HIGH = "high"

def get_model_for_task(task_intensity: ReasoningIntensity) -> str:
    """
    Select the optimal Groq model based on reasoning intensity.
    If using local/gemini defaults, it returns the DEFAULT_MODEL.
    """
    from prompt import DEFAULT_MODEL, PROVIDER
    
    if PROVIDER == ModelProvider.GROQ.value:
        if task_intensity == ReasoningIntensity.HIGH:
            return "llama-3.1-8b-instant"
        return "llama-3.1-8b-instant"
    return DEFAULT_MODEL

def extract_json_from_response(response_text: str) -> str:
    """
    Robustly extract JSON content from LLM response text.
    Handles conversational prefixes/suffixes, markdown blocks, and <think> tags.
    """
    import re
    
    # Remove <think> blocks if present (from reasoning models)
    if "<think>" in response_text:
        response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)

    # Find the first occurrences of { or [ and the last occurrences of } or ]
    match = re.search(r'(\{.*\}|\[.*\])', response_text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # Fallback to current behavior if regex fails
        json_str = response_text.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
    
    # Clean up common JSON-breaking control characters (unescaped newlines in strings)
    # Note: This is a bit risky but often helpful for LLM outputs
    json_str = json_str.strip()
    return json_str


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider based on the model name.
    Implements Failover to Gemini if Groq limits are reached.
    """
    from prompt import GEMINI_API_KEY, GROQ_API_KEY, MODEL_PROVIDER_MAPPING
    
    model_provider = MODEL_PROVIDER_MAPPING.get(model_name, ModelProvider.OLLAMA)
    
    if model_provider == ModelProvider.GEMINI:
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
            logger.warning("⚠️ Gemini API key not found. Falling back to Ollama.")
            return OllamaProvider()
        logger.info(f"🔄 Using Google Gemini API provider with model {model_name}")
        return GeminiProvider(api_key=GEMINI_API_KEY)
        
    elif model_provider == ModelProvider.GROQ:
        if not GROQ_API_KEY:
            logger.warning("⚠️ Groq API key not found. Falling back to Ollama.")
            return OllamaProvider()
            
        primary = GroqProvider(api_key=GROQ_API_KEY)
        
        # Check if Gemini fallback is available
        if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
            logger.info(f"🔄 Using Groq API provider with Gemini Failover for {model_name}")
            secondary = GeminiProvider(api_key=GEMINI_API_KEY)
            # Map Groq models to appropriate Gemini equivalents
            model_map = {
                "llama-3.3-70b-versatile": "gemini-2.0-flash",
                "llama-3.1-8b-instant": "gemini-2.0-flash"
            }
            return FailoverProvider(primary, secondary, model_map)
        
        logger.info(f"🔄 Using Groq API provider with model {model_name} (No Failover)")
        return primary
        
    else:
        logger.info(f"🔄 Using Ollama provider with model {model_name}")
        return OllamaProvider()
