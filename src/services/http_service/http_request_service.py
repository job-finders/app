import httpx
from typing import Optional, Dict, Any, Callable
import asyncio
import logging
from functools import wraps

from src.logger import init_logger

logger = init_logger()


def retry_on_failure(retries: int = 3, delay: float = 1.0, exceptions=(httpx.HTTPError,)):
    """
    Decorator to retry async functions on failure.

    Args:
        retries (int): Number of retry attempts.
        delay (float): Delay in seconds between attempts.
        exceptions (tuple): Exception types to catch and retry on.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    logger.warning(f"Attempt {attempt} failed with {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            raise RuntimeError(f"Operation failed after {retries} attempts.")

        return wrapper
    return decorator


class HttpRequestService:
    """
    HTTP Request Service for both sync and async operations, production-ready.

    Features:
    - Synchronous and asynchronous GET/POST methods
    - Retry logic with logging for async methods
    - Request/response logging (optional)
    - Configurable timeouts and headers
    - Safe for use by AI agents and backend routes
    """

    def __init__(self, timeout: int = 10, log_requests: bool = True):
        """
        Initialize the HTTP request service.

        Args:
            timeout (int): Default timeout (in seconds) for all requests.
            log_requests (bool): Whether to log outgoing requests and responses.
        """
        self.timeout = timeout
        self.log_requests = log_requests

    def _log(self, method: str, url: str, status: Optional[int] = None, extra: Optional[dict] = None):
        if self.log_requests:
            message = f"{method.upper()} {url}"
            if status:
                message += f" -> {status}"
            if extra:
                message += f" | Extra: {extra}"
            logger.info(message)

    def get(self, url: str, headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Synchronous GET request."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=headers, params=params)
            self._log("GET", url, response.status_code, {"params": params})
            response.raise_for_status()
            return response

    def post(self, url: str, headers: Optional[Dict[str, str]] = None,
             json: Optional[Dict[str, Any]] = None,
             data: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Synchronous POST request."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=headers, json=json, data=data)
            self._log("POST", url, response.status_code, {"json": json, "data": data})
            response.raise_for_status()
            return response

    @retry_on_failure(retries=3, delay=1.5)
    async def async_get(self, url: str, headers: Optional[Dict[str, str]] = None,
                        params: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Asynchronous GET request with retry support."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=headers, params=params)
            self._log("GET", url, response.status_code, {"params": params})
            response.raise_for_status()
            return response

    @retry_on_failure(retries=3, delay=1.5)
    async def async_post(self, url: str, headers: Optional[Dict[str, str]] = None,
                         json: Optional[Dict[str, Any]] = None,
                         data: Optional[Dict[str, Any]] = None) -> httpx.Response:
        """Asynchronous POST request with retry support."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=json, data=data)
            self._log("POST", url, response.status_code, {"json": json, "data": data})
            response.raise_for_status()
            return response
