"""Async webhook views for Zalo OA events."""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import IntegrityError
from django.conf import settings
from asgiref.sync import sync_to_async

from .models import WebhookEvent
from .signature import verify_zalo_signature, is_timestamp_valid
from .utils import get_client_ip

logger = logging.getLogger('webhooks')

# Max payload size (1MB)
MAX_PAYLOAD_SIZE = 1_000_000


@csrf_exempt  # Safe: Signature verification authenticates requests
@require_http_methods(["POST"])
async def zalo_webhook(request):
    """
    Main Zalo OA webhook endpoint.

    Receives events from Zalo, verifies signature, stores event.
    Responds quickly (<2s) as required by Zalo.
    """
    client_ip = get_client_ip(request)

    # Get body using sync_to_async to avoid blocking
    raw_body = await sync_to_async(lambda: request.body)()

    # Validate payload size
    if len(raw_body) > MAX_PAYLOAD_SIZE:
        logger.warning(f"Payload too large from {client_ip}: {len(raw_body)} bytes")
        return JsonResponse({'error': 'Payload too large'}, status=413)

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from {client_ip}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # Extract and validate required fields
    event_name = str(payload.get('event_name', 'unknown'))[:100]
    timestamp = payload.get('timestamp', 0)
    app_id = str(payload.get('app_id', ''))[:100]
    signature = request.headers.get('X-ZEvent-Signature', '')

    # Validate app_id matches configured value
    if settings.ZALO_APP_ID and app_id != settings.ZALO_APP_ID:
        logger.warning(f"Invalid app_id from {client_ip}: {app_id}")
        return JsonResponse({'error': 'Invalid app_id'}, status=401)

    # Verify timestamp (replay attack prevention)
    if not is_timestamp_valid(timestamp):
        logger.warning(f"Stale request from {client_ip}, event={event_name}")
        return JsonResponse({'error': 'Stale request'}, status=401)

    # Verify signature
    if not verify_zalo_signature(raw_body, signature, timestamp):
        logger.warning(f"Invalid signature from {client_ip}, event={event_name}")
        return JsonResponse({'error': 'Invalid signature'}, status=401)

    # Extract optional fields with length limits
    message = payload.get('message', {}) if isinstance(payload.get('message'), dict) else {}
    msg_id = str(message.get('msg_id', ''))[:255] or None
    sender = payload.get('sender', {}) if isinstance(payload.get('sender'), dict) else {}
    user_id = str(sender.get('id', ''))[:100]
    oa_id = str(payload.get('oa_id', ''))[:100]

    # Store event asynchronously
    try:
        event = await sync_to_async(WebhookEvent.objects.create)(
            event_name=event_name,
            msg_id=msg_id,
            app_id=app_id,
            oa_id=oa_id,
            user_id=user_id,
            payload=payload,
            timestamp=timestamp,
            signature_verified=True,
            client_ip=client_ip,
            status=WebhookEvent.Status.RECEIVED,
        )
        logger.info(f"Event stored: id={event.id}, type={event_name}, msg_id={msg_id}")

    except IntegrityError:
        # Duplicate msg_id - idempotency check
        logger.info(f"Duplicate event ignored: msg_id={msg_id}")
        return JsonResponse({'status': 'duplicate'}, status=200)

    except Exception as e:
        logger.error(f"Failed to store event: {type(e).__name__}")
        return JsonResponse({'error': 'Storage error'}, status=500)

    return JsonResponse({'status': 'received', 'event_id': event.id}, status=200)


async def health_check(request):
    """Health check endpoint for monitoring."""
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat()
    })
