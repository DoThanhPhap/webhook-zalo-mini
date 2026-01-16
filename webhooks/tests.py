"""Tests for Zalo webhook functionality."""
import json
import hashlib
import time
import pytest
from unittest.mock import patch
from django.test import TestCase, AsyncClient
from django.conf import settings

from .models import WebhookEvent
from .signature import verify_zalo_signature, is_timestamp_valid


class SignatureVerificationTests(TestCase):
    """Test Zalo signature verification logic."""

    def setUp(self):
        self.app_id = 'test_app_123'
        self.secret_key = 'test_secret_456'
        self.timestamp = int(time.time())
        self.body = '{"event_name":"user_send_text","message":{"text":"hello"}}'

    def _generate_signature(self, app_id, body, timestamp, secret):
        """Generate valid signature for testing."""
        base_string = f"{app_id}{body}{timestamp}{secret}"
        return hashlib.sha256(base_string.encode('utf-8')).hexdigest()

    @patch.object(settings, 'ZALO_APP_ID', 'test_app_123')
    @patch.object(settings, 'ZALO_OA_SECRET_KEY', 'test_secret_456')
    def test_valid_signature(self):
        """Valid signature should return True."""
        signature = self._generate_signature(
            self.app_id, self.body, self.timestamp, self.secret_key
        )
        result = verify_zalo_signature(
            self.body.encode('utf-8'),
            signature,
            self.timestamp
        )
        self.assertTrue(result)

    @patch.object(settings, 'ZALO_APP_ID', 'test_app_123')
    @patch.object(settings, 'ZALO_OA_SECRET_KEY', 'test_secret_456')
    def test_invalid_signature(self):
        """Invalid signature should return False."""
        result = verify_zalo_signature(
            self.body.encode('utf-8'),
            'invalid_signature',
            self.timestamp
        )
        self.assertFalse(result)

    @patch.object(settings, 'ZALO_APP_ID', 'test_app_123')
    @patch.object(settings, 'ZALO_OA_SECRET_KEY', 'test_secret_456')
    def test_empty_signature(self):
        """Empty signature should return False."""
        result = verify_zalo_signature(
            self.body.encode('utf-8'),
            '',
            self.timestamp
        )
        self.assertFalse(result)


class TimestampValidationTests(TestCase):
    """Test timestamp validation for replay attack prevention."""

    def test_current_timestamp_valid(self):
        """Current timestamp should be valid."""
        current_ts = int(time.time())
        self.assertTrue(is_timestamp_valid(current_ts))

    def test_old_timestamp_invalid(self):
        """Old timestamp (>5min) should be invalid."""
        old_ts = int(time.time()) - 600  # 10 minutes ago
        self.assertFalse(is_timestamp_valid(old_ts, tolerance=300))

    def test_future_timestamp_invalid(self):
        """Far future timestamp should be invalid."""
        future_ts = int(time.time()) + 600  # 10 minutes ahead
        self.assertFalse(is_timestamp_valid(future_ts, tolerance=300))

    def test_string_timestamp(self):
        """String timestamp should be parsed correctly."""
        current_ts = str(int(time.time()))
        self.assertTrue(is_timestamp_valid(current_ts))

    def test_invalid_format(self):
        """Invalid timestamp format should return False."""
        self.assertFalse(is_timestamp_valid('not_a_number'))
        self.assertFalse(is_timestamp_valid(None))


class WebhookEventModelTests(TestCase):
    """Test WebhookEvent model."""

    def test_create_event(self):
        """Can create webhook event."""
        event = WebhookEvent.objects.create(
            event_name='user_send_text',
            msg_id='msg_123',
            app_id='app_123',
            oa_id='oa_123',
            user_id='user_123',
            payload={'message': {'text': 'hello'}},
            timestamp=int(time.time()),
            signature_verified=True,
            client_ip='192.168.1.1',
        )
        self.assertIsNotNone(event.id)
        self.assertEqual(event.status, WebhookEvent.Status.RECEIVED)

    def test_duplicate_msg_id_rejected(self):
        """Duplicate msg_id should raise error."""
        WebhookEvent.objects.create(
            event_name='user_send_text',
            msg_id='unique_msg_123',
            app_id='app_123',
            payload={},
            timestamp=int(time.time()),
        )
        with self.assertRaises(Exception):
            WebhookEvent.objects.create(
                event_name='user_send_text',
                msg_id='unique_msg_123',  # Same msg_id
                app_id='app_123',
                payload={},
                timestamp=int(time.time()),
            )


@pytest.mark.django_db
class WebhookEndpointTests(TestCase):
    """Test webhook HTTP endpoint."""

    def setUp(self):
        self.client = AsyncClient()
        self.app_id = 'test_app_123'
        self.secret_key = 'test_secret_456'

    def _generate_signature(self, body, timestamp):
        """Generate valid signature."""
        base_string = f"{self.app_id}{body}{timestamp}{self.secret_key}"
        return hashlib.sha256(base_string.encode('utf-8')).hexdigest()

    @patch.object(settings, 'ZALO_APP_ID', 'test_app_123')
    @patch.object(settings, 'ZALO_OA_SECRET_KEY', 'test_secret_456')
    def test_valid_webhook_request(self):
        """Valid webhook request should be accepted."""
        timestamp = int(time.time())
        payload = {
            'event_name': 'user_send_text',
            'app_id': self.app_id,
            'timestamp': timestamp,
            'message': {'msg_id': 'test_msg_001', 'text': 'Hello'},
            'sender': {'id': 'user_123'},
            'oa_id': 'oa_123',
        }
        body = json.dumps(payload)
        signature = self._generate_signature(body, timestamp)

        response = self.client.post(
            '/webhook/zalo/',
            data=body,
            content_type='application/json',
            HTTP_X_ZEVENT_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 200)

    def test_missing_signature(self):
        """Request without signature should be rejected."""
        payload = {
            'event_name': 'user_send_text',
            'timestamp': int(time.time()),
        }
        response = self.client.post(
            '/webhook/zalo/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_json(self):
        """Invalid JSON should return 400."""
        response = self.client.post(
            '/webhook/zalo/',
            data='not valid json',
            content_type='application/json',
            HTTP_X_ZEVENT_SIGNATURE='some_signature',
        )
        self.assertEqual(response.status_code, 400)

    def test_health_check(self):
        """Health check endpoint should return OK."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
