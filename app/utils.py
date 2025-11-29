import logging
import asyncio
import time
from functools import wraps
from typing import Any, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("quiz_solver")

def async_retry(max_attempts: int = 3, delay: float = 1, backoff: float = 2):
    """Retry decorator for async functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            raise last_exception
        return wrapper
    return decorator

class TimeoutError(Exception):
    """Custom timeout error"""
    pass

def timeout(seconds: int):
    """Timeout decorator for async functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), 
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
        return wrapper
    return decorator

def classify_error(error: Exception) -> str:
    """Classify errors for appropriate handling"""
    error_str = str(error).lower()
    
    if any(network_err in error_str for network_err in ['network', 'connection', 'timeout', 'dns']):
        return 'network'
    elif any(auth_err in error_str for auth_err in ['auth', 'unauthorized', 'forbidden', '403']):
        return 'authentication'
    elif any(parse_err in error_str for parse_err in ['parse', 'json', 'decode', 'format']):
        return 'parsing'
    elif any(resource_err in error_str for resource_err in ['resource', 'file', 'download']):
        return 'resource'
    else:
        return 'unknown'