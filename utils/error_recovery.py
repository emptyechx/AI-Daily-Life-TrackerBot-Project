import logging
import asyncio
from typing import Optional, Callable, Any, TypeVar
from functools import wraps

from utils.constants import (
    MSG_ERROR_GENERIC,
    MSG_ERROR_NETWORK,
    MSG_ERROR_DATABASE
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryableError(Exception):
    """Error that can be retried."""
    pass


class FatalError(Exception):
    """Error that should not be retried."""
    pass


async def retry_async(
    func: Callable,
    *args,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs
) -> Optional[Any]:
    """
    Retry async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Function arguments
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier
        **kwargs: Function keyword arguments
    
    Returns:
        Function result or None if all retries failed
    """
    current_delay = delay
    
    for attempt in range(1, max_attempts + 1):
        try:
            result = await func(*args, **kwargs)
            
            if attempt > 1:
                logger.info(f"Success on attempt {attempt} for {func.__name__}")
            
            return result
            
        except FatalError as e:
            logger.error(f"Fatal error in {func.__name__}: {e}")
            return None
            
        except Exception as e:
            if attempt == max_attempts:
                logger.error(
                    f"All {max_attempts} attempts failed for {func.__name__}: {e}",
                    exc_info=True
                )
                return None
            
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                f"Retrying in {current_delay}s..."
            )
            
            await asyncio.sleep(current_delay)
            current_delay *= backoff


def retry_decorator(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
    
    Example:
        @retry_decorator(max_attempts=3)
        async def fetch_data():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(
                func,
                *args,
                max_attempts=max_attempts,
                delay=delay,
                backoff=backoff,
                **kwargs
            )
        return wrapper
    return decorator


def categorize_error(error: Exception) -> str:
    """
    Categorize error for user-friendly messaging.
    
    Args:
        error: Exception instance
    
    Returns:
        Error category: 'network', 'database', 'validation', or 'generic'
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Network errors
    network_keywords = ['connection', 'timeout', 'network', 'unreachable', 'refused']
    if any(keyword in error_str or keyword in error_type for keyword in network_keywords):
        return 'network'
    
    # Database errors
    db_keywords = ['database', 'query', 'table', 'supabase', 'postgres']
    if any(keyword in error_str or keyword in error_type for keyword in db_keywords):
        return 'database'
    
    # Validation errors
    validation_keywords = ['validation', 'invalid', 'value error']
    if any(keyword in error_str or keyword in error_type for keyword in validation_keywords):
        return 'validation'
    
    return 'generic'


def get_user_error_message(error: Exception, context: Optional[str] = None) -> str:
    """
    Get user-friendly error message.
    
    Args:
        error: Exception instance
        context: Optional context (e.g., "saving profile")
    
    Returns:
        User-friendly error message
    """
    category = categorize_error(error)
    
    messages = {
        'network': MSG_ERROR_NETWORK,
        'database': MSG_ERROR_DATABASE,
        'validation': f"⚠️ Invalid input. Please check your data and try again.",
        'generic': MSG_ERROR_GENERIC
    }
    
    base_message = messages.get(category, MSG_ERROR_GENERIC)
    
    if context:
        return f"{base_message}\n<i>Context: {context}</i>"
    
    return base_message


async def safe_execute(
    func: Callable,
    *args,
    error_message: Optional[str] = None,
    log_context: Optional[str] = None,
    **kwargs
) -> tuple[bool, Optional[Any]]:
    """
    Safely execute function with error handling.
    
    Args:
        func: Function to execute
        *args: Function arguments
        error_message: Custom error message for logs
        log_context: Context for logging
        **kwargs: Function keyword arguments
    
    Returns:
        Tuple of (success, result)
    """
    try:
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        
        return True, result
        
    except Exception as e:
        context = log_context or func.__name__
        logger.error(
            f"Error in {context}: {error_message or str(e)}",
            exc_info=True
        )
        return False, None


class ErrorHandler:
    """Context manager for error handling with user feedback."""
    
    def __init__(
        self,
        message_func: Optional[Callable] = None,
        show_errors: bool = True,
        context: Optional[str] = None
    ):
        """
        Initialize error handler.
        
        Args:
            message_func: Optional function to send messages to user
            show_errors: Whether to show errors to user
            context: Context for error messages
        """
        self.message_func = message_func
        self.show_errors = show_errors
        self.context = context
        self.error = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            
            # Log error
            logger.error(
                f"Error in {self.context or 'operation'}: {exc_val}",
                exc_info=True
            )
            
            # Show to user if requested
            if self.show_errors and self.message_func:
                error_msg = get_user_error_message(exc_val, self.context)
                try:
                    await self.message_func(error_msg)
                except Exception as e:
                    logger.error(f"Failed to send error message to user: {e}")
            
            # Suppress exception (handled)
            return True
        
        return False


def log_function_call(func):
    """Decorator to log function calls and errors."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"Calling {func_name}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"{func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func_name} failed: {e}", exc_info=True)
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"Calling {func_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func_name} failed: {e}", exc_info=True)
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# Specific error handlers for common operations

async def safe_db_operation(
    operation: Callable,
    *args,
    operation_name: str = "database operation",
    **kwargs
) -> Optional[Any]:
    """
    Execute database operation with retry logic.
    
    Args:
        operation: Database function to execute
        *args: Function arguments
        operation_name: Name for logging
        **kwargs: Function keyword arguments
    
    Returns:
        Operation result or None
    """
    return await retry_async(
        operation,
        *args,
        max_attempts=3,
        delay=0.5,
        **kwargs
    )


async def safe_ai_operation(
    operation: Callable,
    *args,
    fallback_response: Optional[str] = None,
    **kwargs
) -> Optional[str]:
    """
    Execute AI operation with fallback.
    
    Args:
        operation: AI function to execute
        *args: Function arguments
        fallback_response: Response to return if AI fails
        **kwargs: Function keyword arguments
    
    Returns:
        AI response or fallback
    """
    try:
        result = await operation(*args, **kwargs)
        return result if result else fallback_response
    except Exception as e:
        logger.error(f"AI operation failed: {e}")
        return fallback_response