"""Security middleware for webhook endpoints."""
import logging
import time
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
from asgiref.sync import sync_to_async, iscoroutinefunction

from .utils import get_client_ip

logger = logging.getLogger('webhooks')


class RateLimitMiddleware:
    """
    Rate limiting middleware using Redis with atomic operations.
    Supports both sync and async modes.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 100)
        self.async_mode = iscoroutinefunction(get_response)

    def __call__(self, request):
        if self.async_mode:
            return self._async_call(request)
        return self._sync_call(request)

    async def _async_call(self, request):
        """Async rate limiting handler."""
        if not request.path.startswith('/webhook'):
            return await self.get_response(request)

        client_ip = get_client_ip(request)
        if await self._is_rate_limited_async(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)

        return await self.get_response(request)

    def _sync_call(self, request):
        """Sync rate limiting handler."""
        if not request.path.startswith('/webhook'):
            return self.get_response(request)

        client_ip = get_client_ip(request)
        if self._is_rate_limited_sync(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)

        return self.get_response(request)

    async def _is_rate_limited_async(self, client_ip: str) -> bool:
        """Check rate limit using async cache operations."""
        cache_key = f'ratelimit:{client_ip}'
        try:
            # Atomic increment - prevents race condition
            current = await sync_to_async(cache.incr)(cache_key)
            if current == 1:
                # First request in window, set expiry
                await sync_to_async(cache.expire)(cache_key, 60)
            return current > self.rate_limit
        except ValueError:
            # Key doesn't exist, initialize it
            await sync_to_async(cache.set)(cache_key, 1, timeout=60)
            return False
        except Exception as e:
            logger.error(f"Rate limit cache error: {e}")
            return False

    def _is_rate_limited_sync(self, client_ip: str) -> bool:
        """Check rate limit using sync cache operations."""
        cache_key = f'ratelimit:{client_ip}'
        try:
            current = cache.incr(cache_key)
            if current == 1:
                cache.expire(cache_key, 60)
            return current > self.rate_limit
        except ValueError:
            cache.set(cache_key, 1, timeout=60)
            return False
        except Exception as e:
            logger.error(f"Rate limit cache error: {e}")
            return False


class RequestLoggingMiddleware:
    """
    Log all webhook requests for audit trail.
    Supports both sync and async modes.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.async_mode = iscoroutinefunction(get_response)

    def __call__(self, request):
        if self.async_mode:
            return self._async_call(request)
        return self._sync_call(request)

    async def _async_call(self, request):
        """Async logging handler."""
        if not request.path.startswith('/webhook'):
            return await self.get_response(request)

        start_time = time.time()
        client_ip = get_client_ip(request)

        logger.debug(
            f"Incoming: {request.method} {request.path} from {client_ip}"
        )

        response = await self.get_response(request)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Completed: {request.method} {request.path} "
            f"status={response.status_code} duration={duration_ms:.2f}ms"
        )

        return response

    def _sync_call(self, request):
        """Sync logging handler."""
        if not request.path.startswith('/webhook'):
            return self.get_response(request)

        start_time = time.time()
        client_ip = get_client_ip(request)

        logger.debug(
            f"Incoming: {request.method} {request.path} from {client_ip}"
        )

        response = self.get_response(request)

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Completed: {request.method} {request.path} "
            f"status={response.status_code} duration={duration_ms:.2f}ms"
        )

        return response
