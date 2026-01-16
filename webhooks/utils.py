"""Shared utility functions for webhook handling."""


def get_client_ip(request) -> str:
    """
    Extract client IP from request, handling proxy headers.

    Args:
        request: Django HTTP request object

    Returns:
        Client IP address as string
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
