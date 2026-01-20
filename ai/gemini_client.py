import logging
import google.generativeai as genai
from typing import Optional
from functools import lru_cache
from config import get_gemini_api_key

logger = logging.getLogger(__name__)

# Global model instance
_model = None
_configured = False


def configure_gemini() -> None:
    """
    Configure Gemini API (called once at startup).
    
    Raises:
        Exception: If configuration fails
    """
    global _configured
    
    if _configured:
        return
    
    try:
        genai.configure(api_key=get_gemini_api_key())
        _configured = True
        logger.info("Gemini AI configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Gemini: {e}")
        raise


def get_model(model_name: str = "gemini-2.5-flash"):
    """
    Get or create Gemini model instance.
    
    Args:
        model_name: Model to use (default: gemini-2.5-flash for fast responses)
    
    Returns:
        GenerativeModel instance or None if unavailable
    """
    global _model
    
    if not _configured:
        configure_gemini()
    
    if _model is None:
        try:
            _model = genai.GenerativeModel(model_name)
            logger.info(f"Gemini model created: {model_name}")
        except Exception as e:
            logger.error(f"Failed to create Gemini model: {e}")
            return None
    
    return _model


def is_ai_available() -> bool:
    """
    Check if AI service is available.
    
    Returns:
        True if AI is ready to use
    """
    try:
        model = get_model()
        return model is not None
    except Exception:
        return False


async def generate_content_safe(prompt: str, max_length: int = 2000) -> Optional[str]:
    """
    Generate content with safety checks and error handling.
    
    Args:
        prompt: Input prompt for the model
        max_length: Maximum output tokens
    
    Returns:
        Generated text or None if failed
    """
    model = get_model()
    if not model:
        logger.warning("AI model not available")
        return None
    
    try:
        # Pass token limit directly to the model
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_length 
            )
        )
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Error generating content: {e}", exc_info=True)
        return None


# Cache for repeated prompts (Issue #15)
@lru_cache(maxsize=100)
def get_cached_template_response(template_key: str) -> Optional[str]:
    """
    Get cached response for template prompts.
    
    Args:
        template_key: Unique key for the template
    
    Returns:
        Cached response or None
    
    Note:
        This is a simple cache - can be expanded with Redis later
    """
    return None