"""Zalo webhook signature verification utilities."""
import hashlib
import hmac
import time
import logging
from django.conf import settings

logger = logging.getLogger('webhooks')


def verify_zalo_signature(
    raw_body: bytes,
    signature: str,
    timestamp: int | str,
    app_id: str | None = None,
    secret_key: str | None = None
) -> bool:
    """
    Verify Zalo webhook signature using HMAC-SHA256.

    Formula: sha256(appId + rawBody + timestamp + OAsecretKey)

    Args:
        raw_body: Raw HTTP request body (bytes)
        signature: X-ZEvent-Signature header value
        timestamp: Event timestamp from payload
        app_id: Zalo App ID (uses settings if not provided)
        secret_key: OA Secret Key (uses settings if not provided)

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature:
        logger.warning("Missing signature header")
        return False

    app_id = app_id or settings.ZALO_APP_ID
    secret_key = secret_key or settings.ZALO_OA_SECRET_KEY

    if not app_id or not secret_key:
        logger.error("Missing ZALO_APP_ID or ZALO_OA_SECRET_KEY configuration")
        return False

    # Build signature string: appId + body + timestamp + secretKey
    body_str = raw_body.decode('utf-8') if isinstance(raw_body, bytes) else raw_body
    base_string = f"{app_id}{body_str}{timestamp}{secret_key}"

    # Calculate expected signature
    expected_signature = hashlib.sha256(base_string.encode('utf-8')).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(signature.lower(), expected_signature.lower())

    if not is_valid:
        logger.warning(f"Signature mismatch: received={signature[:16]}...")

    return is_valid


def is_timestamp_valid(timestamp: int | str, tolerance: int | None = None) -> bool:
    """
    Check if timestamp is within acceptable range (prevent replay attacks).

    Args:
        timestamp: Event timestamp (Unix seconds)
        tolerance: Max age in seconds (uses settings if not provided)

    Returns:
        True if timestamp is recent enough
    """
    tolerance = tolerance or settings.WEBHOOK_TIMESTAMP_TOLERANCE

    try:
        ts = int(timestamp)
        now = int(time.time())
        age = abs(now - ts)
        is_valid = age <= tolerance

        if not is_valid:
            logger.warning(f"Stale timestamp: age={age}s, tolerance={tolerance}s")

        return is_valid

    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid timestamp format: {timestamp}, error: {e}")
        return False
