# Zalo Webhook - Django Application

Django 6.0 async application to receive and process Zalo Official Account webhook events.

## Features

- Async webhook endpoint with Django 6.0
- HMAC-SHA256 signature verification
- PostgreSQL event storage with idempotency
- Redis-based rate limiting (100 req/min)
- Docker deployment ready
- Comprehensive logging

## Tech Stack

- Django 6.0 (async views)
- PostgreSQL 16
- Redis 7
- Docker + Docker Compose
- uvicorn (ASGI server)

## Quick Start

See [../SETUP.md](../SETUP.md) for detailed setup instructions.

```bash
# Clone and setup
cp .env.example .env
# Edit .env with your Zalo credentials

# Start with Docker
docker compose up -d

# Verify
curl http://localhost:8000/health/
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook/zalo/` | POST | Receive Zalo OA events |
| `/health/` | GET | Health check |

## Project Structure

```
WebHookZalo/
├── config/               # Django settings
│   ├── settings.py       # Main configuration
│   ├── urls.py           # URL routing
│   └── asgi.py           # ASGI entry point
├── webhooks/             # Core webhook app
│   ├── views.py          # Async webhook handlers
│   ├── models.py         # WebhookEvent model
│   ├── middleware.py     # Rate limiting, logging
│   ├── signature.py      # HMAC-SHA256 verification
│   └── tests.py          # Unit tests
├── docs/                 # Documentation
├── docker-compose.yml    # Docker setup
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Configuration

Environment variables:

| Variable | Description |
|----------|-------------|
| `ZALO_APP_ID` | Zalo App ID |
| `ZALO_OA_SECRET_KEY` | Zalo OA Secret Key |
| `SECRET_KEY` | Django secret key |
| `DATABASE_*` | PostgreSQL connection |
| `REDIS_URL` | Redis connection |
| `RATE_LIMIT_PER_MINUTE` | Rate limit (default: 100) |

## Zalo Webhook Events

Supported events:
- `user_send_text` - Text message
- `user_send_image` - Image attachment
- `user_send_file` - File attachment
- `user_send_location` - Location sharing
- `follow` / `unfollow` - User follow events

## Security

- HMAC-SHA256 signature verification
- Timestamp validation (5 min tolerance)
- Rate limiting per IP
- HTTPS required in production

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Run dev server
python manage.py runserver

# Run tests
pytest
```

## License

MIT
