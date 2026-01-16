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


@csrf_exempt
@require_http_methods(["POST"])
async def zalo_webhook(request):
    """
    Main Zalo OA webhook endpoint.

    Receives events from Zalo, verifies signature, stores event.
    Responds quickly (<2s) as required by Zalo.
    """
    client_ip = get_client_ip(request)

    # Get body
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

    # Extract fields
    event_name = str(payload.get('event_name', 'unknown'))[:100]
    timestamp = payload.get('timestamp', 0)
    app_id = str(payload.get('app_id', ''))[:100]
    signature = request.headers.get('X-ZEvent-Signature', '')

    # Log incoming request
    logger.info(f"Webhook received: event={event_name}, app_id={app_id}, ip={client_ip}")

    # Check if signature verification should be skipped
    skip_verification = getattr(settings, 'SKIP_SIGNATURE_VERIFICATION', False)
    signature_verified = False

    if not skip_verification:
        # Validate app_id
        if settings.ZALO_APP_ID and app_id and app_id != settings.ZALO_APP_ID:
            logger.warning(f"Invalid app_id from {client_ip}: {app_id}")
            return JsonResponse({'error': 'Invalid app_id'}, status=401)

        # Verify timestamp
        if timestamp and not is_timestamp_valid(timestamp):
            logger.warning(f"Stale request from {client_ip}, event={event_name}")
            return JsonResponse({'error': 'Stale request'}, status=401)

        # Verify signature
        if signature and not verify_zalo_signature(raw_body, signature, timestamp):
            logger.warning(f"Invalid signature from {client_ip}, event={event_name}")
            return JsonResponse({'error': 'Invalid signature'}, status=401)

        signature_verified = bool(signature)
    else:
        logger.info("Signature verification skipped (SKIP_SIGNATURE_VERIFICATION=true)")

    # Extract optional fields
    message = payload.get('message', {}) if isinstance(payload.get('message'), dict) else {}
    msg_id = str(message.get('msg_id', ''))[:255] or None
    sender = payload.get('sender', {}) if isinstance(payload.get('sender'), dict) else {}
    user_id = str(sender.get('id', ''))[:100]
    oa_id = str(payload.get('oa_id', ''))[:100]

    # Store event
    try:
        event = await sync_to_async(WebhookEvent.objects.create)(
            event_name=event_name,
            msg_id=msg_id,
            app_id=app_id,
            oa_id=oa_id,
            user_id=user_id,
            payload=payload,
            timestamp=timestamp or 0,
            signature_verified=signature_verified,
            client_ip=client_ip,
            status=WebhookEvent.Status.RECEIVED,
        )
        logger.info(f"Event stored: id={event.id}, type={event_name}")

    except IntegrityError:
        logger.info(f"Duplicate event ignored: msg_id={msg_id}")
        return JsonResponse({'status': 'duplicate'}, status=200)

    except Exception as e:
        logger.error(f"Failed to store event: {type(e).__name__}: {e}")
        # Still return 200 to acknowledge receipt
        return JsonResponse({'status': 'received', 'stored': False}, status=200)

    return JsonResponse({'status': 'received', 'event_id': event.id}, status=200)


async def health_check(request):
    """Health check endpoint for monitoring."""
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat()
    })
