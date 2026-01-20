import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

def get_env_variable(name: str, default: Optional[str] = None) -> str:
    """Retrieves an environment variable or raises ValueError if missing."""
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Environment variable {name} is not set")
    return value


def get_bot_token() -> str:
    """Get Telegram bot token from environment."""
    return get_env_variable("BOT_TOKEN")


def get_supabase_url() -> str:
    """Get Supabase URL from environment."""
    return get_env_variable("SUPABASE_URL")


def get_supabase_key() -> str:
    """Get Supabase API key from environment."""
    return get_env_variable("SUPABASE_KEY")

def get_gemini_api_key() -> str:
    """Get Gemini API key from environment."""
    return get_env_variable("GEMINI_API_KEY") 