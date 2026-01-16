"""Webhook event storage models."""
from django.db import models


class WebhookEvent(models.Model):
    """Stores incoming Zalo webhook events."""

    class Status(models.TextChoices):
        RECEIVED = 'received', 'Received'
        PROCESSING = 'processing', 'Processing'
        PROCESSED = 'processed', 'Processed'
        FAILED = 'failed', 'Failed'

    # Event identification
    event_name = models.CharField(max_length=100, db_index=True)
    msg_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    # Zalo metadata
    app_id = models.CharField(max_length=100)
    oa_id = models.CharField(max_length=100, blank=True)
    user_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Event data
    payload = models.JSONField()
    timestamp = models.BigIntegerField()

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
        db_index=True
    )

    # Security audit
    signature_verified = models.BooleanField(default=False)
    client_ip = models.GenericIPAddressField(null=True, blank=True)

    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['event_name', 'received_at']),
            models.Index(fields=['status', 'received_at']),
        ]

    def __str__(self):
        return f"{self.event_name} - {self.msg_id or 'no-msg-id'}"
