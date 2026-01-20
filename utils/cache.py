import logging
import time
from typing import Any, Optional, Callable
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

# Simple in-memory cache
_cache = {}
_cache_timestamps = {}


def _is_expired(key: str, ttl: int) -> bool:
    """Check if cache entry has expired."""
    if key not in _cache_timestamps:
        return True
    
    elapsed = time.time() - _cache_timestamps[key]
    return elapsed > ttl


def get_cached(key: str, ttl: int = 600) -> Optional[Any]:
    """
    Get value from cache if not expired.
    
    Args:
        key: Cache key
        ttl: Time to live in seconds
    
    Returns:
        Cached value or None
    """
    if key not in _cache:
        return None
    
    if _is_expired(key, ttl):
        # Remove expired entry
        _cache.pop(key, None)
        _cache_timestamps.pop(key, None)
        return None
    
    logger.debug(f"Cache HIT: {key}")
    return _cache[key]


def set_cached(key: str, value: Any) -> None:
    """
    Store value in cache.
    
    Args:
        key: Cache key
        value: Value to store
    """
    _cache[key] = value
    _cache_timestamps[key] = time.time()
    logger.debug(f"Cache SET: {key}")


def invalidate_cache(key: str) -> None:
    """
    Remove entry from cache.
    
    Args:
        key: Cache key to remove
    """
    _cache.pop(key, None)
    _cache_timestamps.pop(key, None)
    logger.debug(f"Cache INVALIDATE: {key}")


def invalidate_pattern(pattern: str) -> int:
    """
    Remove all cache entries matching pattern.
    
    Args:
        pattern: Pattern to match (simple substring match)
    
    Returns:
        Number of entries removed
    """
    keys_to_remove = [k for k in _cache.keys() if pattern in k]
    
    for key in keys_to_remove:
        invalidate_cache(key)
    
    logger.debug(f"Cache INVALIDATE PATTERN: {pattern} ({len(keys_to_remove)} entries)")
    return len(keys_to_remove)


def clear_cache() -> None:
    """Clear entire cache."""
    _cache.clear()
    _cache_timestamps.clear()
    logger.info("Cache CLEARED")


def cache_async(ttl: int = 600, key_func: Optional[Callable] = None):
    """
    Decorator for caching async function results.
    
    Args:
        ttl: Time to live in seconds
        key_func: Optional function to generate cache key from args
    
    Example:
        @cache_async(ttl=3600)
        async def expensive_operation(user_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name and args
                cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Check cache
            cached_value = get_cached(cache_key, ttl)
            if cached_value is not None:
                return cached_value
            
            # Call function
            logger.debug(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                set_cached(cache_key, result)
            
            return result
        
        return wrapper
    return decorator


# Specific cache key generators for common operations

def weekly_stats_key(user_id: int, week_start: str) -> str:
    """Generate cache key for weekly statistics."""
    return f"weekly_stats:{user_id}:{week_start}"


def user_profile_key(user_id: int) -> str:
    """Generate cache key for user profile."""
    return f"user_profile:{user_id}"


def tag_extraction_key(text: str) -> str:
    """Generate cache key for tag extraction (hash of text)."""
    import hashlib
    text_hash = hashlib.md5(text.encode()).hexdigest()
    return f"tags:{text_hash}"


def invalidate_user_cache(user_id: int) -> None:
    """Invalidate all cache entries for a user."""
    invalidate_pattern(f":{user_id}:")
    logger.info(f"Invalidated cache for user {user_id}")


# Cache statistics
def get_cache_stats() -> dict:
    """Get cache statistics for monitoring."""
    total_entries = len(_cache)
    
    # Count expired entries
    current_time = time.time()
    expired = sum(
        1 for timestamp in _cache_timestamps.values()
        if (current_time - timestamp) > 600  # Default 10min TTL
    )
    
    return {
        'total_entries': total_entries,
        'expired_entries': expired,
        'active_entries': total_entries - expired,
        'cache_size_bytes': sum(
            len(str(v)) for v in _cache.values()
        )
    }


# Periodic cleanup task (optional)
async def cleanup_expired_cache(interval: int = 300):
    """
    Background task to clean up expired cache entries.
    
    Args:
        interval: Cleanup interval in seconds
    """
    while True:
        await asyncio.sleep(interval)
        
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in _cache_timestamps.items()
            if (current_time - timestamp) > 3600  # Remove after 1 hour
        ]
        
        for key in expired_keys:
            invalidate_cache(key)
        
        if expired_keys:
            logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries")