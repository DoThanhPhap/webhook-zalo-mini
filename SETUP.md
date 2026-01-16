# Zalo Webhook - Setup Guide

## Prerequisites

- Docker & Docker Compose
- Zalo OA account + Developer account
- Zalo App ID & OA Secret Key (from [developers.zalo.me](https://developers.zalo.me))

## Quick Start

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Edit `.env` with your credentials

```env
# Required - Get from Zalo Developer Portal
ZALO_APP_ID=your_app_id_here
ZALO_OA_SECRET_KEY=your_oa_secret_key_here

# Security - Generate strong secret
SECRET_KEY=your-django-secret-key-min-50-chars

# Optional - Database password
DATABASE_PASSWORD=your_secure_db_password
```

**How to get Zalo credentials:**
1. Go to [developers.zalo.me](https://developers.zalo.me)
2. Select your app or create new one
3. Go to **Settings** tab -> Copy **App ID**
4. Go to **Webhook** section -> Copy **OA Secret Key**

### 3. Start Services

```bash
docker compose up -d
```

This starts:
- **web**: Django app on port 8000
- **db**: PostgreSQL on port 5432
- **cache**: Redis on port 6379

### 4. Verify Running

```bash
# Check health endpoint
curl http://localhost:8000/health/

# Expected response:
# {"status": "ok", "timestamp": "2026-01-16T12:00:00+07:00"}
```

### 5. Configure Zalo Webhook

1. Go to [developers.zalo.me](https://developers.zalo.me) -> Your App -> Webhook
2. Set Webhook URL: `https://your-domain.com/webhook/zalo/`
3. Select events to receive
4. Save configuration

**Note:** Zalo requires HTTPS. For local development:
- Use [ngrok](https://ngrok.com): `ngrok http 8000`
- Use the ngrok URL as webhook endpoint

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ZALO_APP_ID` | Yes | - | Zalo App ID |
| `ZALO_OA_SECRET_KEY` | Yes | - | Zalo OA Secret Key |
| `SECRET_KEY` | Yes | - | Django secret key |
| `DEBUG` | No | `False` | Enable debug mode |
| `DATABASE_PASSWORD` | No | `webhook_pass` | PostgreSQL password |
| `RATE_LIMIT_PER_MINUTE` | No | `100` | Rate limit |

## Common Commands

```bash
# View logs
docker compose logs -f web

# Stop services
docker compose down

# Rebuild after code changes
docker compose up -d --build

# Run migrations manually
docker compose exec web python manage.py migrate

# Access database
docker compose exec db psql -U webhook_user -d webhook_db
```

## Testing Webhook

Send test request:

```bash
curl -X POST http://localhost:8000/webhook/zalo/ \
  -H "Content-Type: application/json" \
  -H "X-ZEvent-Signature: your_signature" \
  -d '{"event_name":"user_send_text","timestamp":1234567890,"app_id":"your_app_id"}'
```

## Troubleshooting

### Port already in use
```bash
# Find process using port
netstat -ano | findstr :8000

# Kill process (Windows)
taskkill /PID <pid> /F
```

### Database connection error
```bash
# Check if PostgreSQL is running
docker compose ps

# Restart database
docker compose restart db
```

### Redis connection error
```bash
# Check Redis
docker compose exec cache redis-cli ping
# Should return: PONG
```

## Security Checklist

- [ ] Change `SECRET_KEY` in production
- [ ] Change `DATABASE_PASSWORD` in production
- [ ] Set `DEBUG=False` in production
- [ ] Use HTTPS for webhook endpoint
- [ ] Configure firewall rules
- [ ] Enable Zalo IP allowlisting (if available)

## Next Steps

1. Configure Zalo webhook URL
2. Test with Zalo test events
3. Implement event handlers in `webhooks/handlers.py`
4. Monitor logs for incoming events

For more details, see [docs/README.md](docs/README.md)
