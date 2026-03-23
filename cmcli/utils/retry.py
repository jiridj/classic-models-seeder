"""Retry utilities with exponential backoff."""

import time
from functools import wraps
from typing import Callable, Type, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """Decorator to retry a function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry with (exception, attempt)
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            delay = initial_delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    
                    if attempt >= max_attempts:
                        logger.error(f"Max retry attempts ({max_attempts}) reached for {func.__name__}")
                        raise
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            
            # Should never reach here, but just in case
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: int, per: float):
        """Initialize rate limiter.
        
        Args:
            rate: Number of requests allowed
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        current = time.time()
        time_passed = current - self.last_check
        self.last_check = current
        
        # Add tokens based on time passed
        self.allowance += time_passed * (self.rate / self.per)
        
        if self.allowance > self.rate:
            self.allowance = self.rate
        
        if self.allowance < 1.0:
            # Need to wait
            sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
            logger.debug(f"Rate limit reached, waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)
            self.allowance = 0.0
        else:
            self.allowance -= 1.0

# Made with Bob
