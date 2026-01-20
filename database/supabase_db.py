import logging
import functools
import asyncio
from typing import Optional, Any, Callable
from supabase import create_client, Client

from config import get_supabase_url, get_supabase_key

logger = logging.getLogger(__name__)


def get_supabase() -> Client:
    """
    Create a new Supabase client for each operation.
    
    Pattern explanation:
    - We create a fresh client per operation instead of reusing a global instance
    - This avoids connection reuse issues in async environments
    - Each async operation gets its own isolated client
    - Safe for concurrent operations across multiple users
    
    Returns:
        New Supabase client instance
    """
    return create_client(get_supabase_url(), get_supabase_key())


def handle_db_errors(default_return: Any = None):
    """
    Decorator for handling database errors consistently.
    
    Args:
        default_return: Value to return if operation fails
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Database error in {func.__name__}: {e}", exc_info=True)
                return default_return
        return wrapper
    return decorator


@handle_db_errors(default_return=None)
async def get_user_profile(telegram_id: int) -> Optional[dict]:
    """
    Get user profile by Telegram ID.
    
    Args:
        telegram_id: User's Telegram ID
    
    Returns:
        User profile dict or None if not found
    """
    client = get_supabase()
    response = await asyncio.to_thread(
        lambda: client.table("profiles").select("*").eq("telegram_id", telegram_id).execute()
    )
    return response.data[0] if response.data else None


@handle_db_errors(default_return=None)
async def create_profile(profile_data: dict) -> Optional[dict]:
    """
    Create a new user profile.
    
    Args:
        profile_data: Dictionary with profile fields
    
    Returns:
        Created profile data or None if failed
    """
    client = get_supabase()
    response = await asyncio.to_thread(
        lambda: client.table("profiles").insert(profile_data).execute()
    )
    return response.data


@handle_db_errors(default_return=None)
async def update_user_profile(
    telegram_id: int,
    update_data: dict
) -> Optional[dict]:
    """
    Update existing user profile.
    
    Args:
        telegram_id: User's Telegram ID
        update_data: Dictionary with fields to update
    
    Returns:
        Updated profile data or None if failed
    """
    client = get_supabase()
    response = await asyncio.to_thread(
        lambda: client.table("profiles").update(update_data).eq("telegram_id", telegram_id).execute()
    )
    return response.data


@handle_db_errors(default_return=False)
async def delete_user_profile(telegram_id: int) -> bool:
    """
    Delete user profile and all related data.
    
    Args:
        telegram_id: User's Telegram ID
    
    Returns:
        True if successful, False otherwise
    """
    client = get_supabase()
    
    # Delete all entries first
    await asyncio.to_thread(
        lambda: client.table("entries").delete().eq("telegram_id", telegram_id).execute()
    )

    # Then delete profile
    response = await asyncio.to_thread(
        lambda: client.table("profiles").delete().eq("telegram_id", telegram_id).execute()
    )
    return bool(response.data)


@handle_db_errors(default_return=[])
async def get_all_profiles() -> list[dict]:
    """
    Get all user profiles (admin function).
    
    Returns:
        List of all profiles
    """
    client = get_supabase()
    response = await asyncio.to_thread(
        lambda: client.table("profiles").select("*").execute()
    )
    return response.data