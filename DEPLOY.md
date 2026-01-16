# Deploy Zalo Webhook trên Ubuntu 22.04 với Docker

## Thông tin
- **Server**: Ubuntu 22.04 LTS
- **URL**: `https://hr.truonggia.vn/app/webhook`
- **Stack**: Docker + Nginx + Let's Encrypt SSL

---

## Bước 1: SSH vào Server

```bash
ssh user@your-server-ip
```

---

## Bước 2: Cài đặt Docker (nếu chưa có)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Cài Docker
curl -fsSL https://get.docker.com | sudo sh

# Thêm user vào docker group
sudo usermod -aG docker $USER

# Logout và login lại để áp dụng
exit
# SSH lại vào server

# Verify
docker --version
docker compose version
```

---

## Bước 3: Cài Nginx + Certbot

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

---

## Bước 4: Clone Project

```bash
# Tạo thư mục
sudo mkdir -p /opt/apps
cd /opt/apps

# Clone từ GitHub
sudo git clone https://github.com/DoThanhPhap/webhook-zalo-mini.git zalo-webhook
cd zalo-webhook

# Đổi owner
sudo chown -R $USER:$USER /opt/apps/zalo-webhook
```

---

## Bước 5: Cấu hình Environment

```bash
# Copy file mẫu
cp .env.example .env

# Chỉnh sửa .env
nano .env
```

**Nội dung .env:**
```env
# Django
DEBUG=False
SECRET_KEY=thay-bang-key-dai-it-nhat-50-ky-tu-ngau-nhien
ALLOWED_HOSTS=hr.truonggia.vn,localhost

# Database
DATABASE_NAME=webhook_db
DATABASE_USER=webhook_user
DATABASE_PASSWORD=mat-khau-manh-cho-database
DATABASE_HOST=db
DATABASE_PORT=5432

# Redis
REDIS_URL=redis://cache:6379/0

# Zalo - Lấy từ developers.zalo.me
ZALO_APP_ID=your_app_id
ZALO_OA_SECRET_KEY=your_secret_key

# Rate limit
RATE_LIMIT_PER_MINUTE=100
```

**Tạo SECRET_KEY ngẫu nhiên:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Bước 6: Chỉnh Docker Compose cho Production

Tạo file `docker-compose.prod.yml`:

```bash
nano docker-compose.prod.yml
```

**Nội dung:**
```yaml
services:
  web:
    build: .
    restart: always
    expose:
      - "8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS:-hr.truonggia.vn,localhost}
      - DATABASE_NAME=${DATABASE_NAME:-webhook_db}
      - DATABASE_USER=${DATABASE_USER:-webhook_user}
      - DATABASE_PASSWORD=${DATABASE_PASSWORD}
      - DATABASE_HOST=db
      - DATABASE_PORT=5432
      - REDIS_URL=redis://cache:6379/0
      - ZALO_APP_ID=${ZALO_APP_ID}
      - ZALO_OA_SECRET_KEY=${ZALO_OA_SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    volumes:
      - ./logs:/app/logs
    command: >
      sh -c "python manage.py migrate --noinput &&
             gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000"
    networks:
      - webhook-network

  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_DB: ${DATABASE_NAME:-webhook_db}
      POSTGRES_USER: ${DATABASE_USER:-webhook_user}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER:-webhook_user} -d ${DATABASE_NAME:-webhook_db}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - webhook-network

  cache:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data
    networks:
      - webhook-network

volumes:
  postgres_data:
  redis_data:

networks:
  webhook-network:
    driver: bridge
```

---

## Bước 7: Cấu hình Nginx

```bash
sudo nano /etc/nginx/sites-available/hr.truonggia.vn
```

**Nội dung:**
```nginx
server {
    listen 80;
    server_name hr.truonggia.vn;

    # Webhook endpoint - proxy to Docker
    location /app/webhook {
        # Rewrite path: /app/webhook -> /webhook/zalo/
        rewrite ^/app/webhook(.*)$ /webhook/zalo/$1 break;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout cho webhook
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /app/webhook/health {
        rewrite ^/app/webhook/health$ /health/ break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Block các request khác đến webhook path
    location / {
        # Nếu có app khác tại hr.truonggia.vn, config ở đây
        return 404;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/hr.truonggia.vn /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## Bước 8: Cài SSL với Let's Encrypt

```bash
sudo certbot --nginx -d hr.truonggia.vn
```

- Nhập email
- Đồng ý terms
- Chọn redirect HTTP to HTTPS

**Auto-renew đã được cài tự động. Kiểm tra:**
```bash
sudo certbot renew --dry-run
```

---

## Bước 9: Chạy Docker

```bash
cd /opt/apps/zalo-webhook

# Build và chạy
docker compose -f docker-compose.prod.yml up -d --build

# Kiểm tra logs
docker compose -f docker-compose.prod.yml logs -f web

# Kiểm tra status
docker compose -f docker-compose.prod.yml ps
```

---

## Bước 10: Verify

```bash
# Test health check
curl https://hr.truonggia.vn/app/webhook/health

# Expected response:
# {"status": "ok", "timestamp": "..."}
```

---

## Bước 11: Cấu hình Zalo Webhook

1. Truy cập [developers.zalo.me](https://developers.zalo.me)
2. Chọn App của bạn
3. Vào **Webhook** section
4. Đặt URL: `https://hr.truonggia.vn/app/webhook`
5. Chọn events cần nhận
6. Save

---

## Các lệnh quản lý

```bash
cd /opt/apps/zalo-webhook

# Xem logs
docker compose -f docker-compose.prod.yml logs -f web

# Restart
docker compose -f docker-compose.prod.yml restart

# Stop
docker compose -f docker-compose.prod.yml down

# Update code từ GitHub
git pull origin master
docker compose -f docker-compose.prod.yml up -d --build

# Xem events trong database
docker compose -f docker-compose.prod.yml exec db psql -U webhook_user -d webhook_db -c "SELECT * FROM webhooks_webhookevent ORDER BY received_at DESC LIMIT 10;"
```

---

## Troubleshooting

### Lỗi 502 Bad Gateway
```bash
# Kiểm tra Docker đang chạy
docker compose -f docker-compose.prod.yml ps

# Kiểm tra logs
docker compose -f docker-compose.prod.yml logs web
```

### Lỗi kết nối Database
```bash
# Kiểm tra DB container
docker compose -f docker-compose.prod.yml logs db

# Restart DB
docker compose -f docker-compose.prod.yml restart db
```

### Signature verification failed
- Kiểm tra `ZALO_APP_ID` và `ZALO_OA_SECRET_KEY` trong `.env`
- Restart app sau khi sửa: `docker compose -f docker-compose.prod.yml restart web`

---

## Firewall (UFW)

```bash
# Cho phép SSH, HTTP, HTTPS
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

---

## Security Checklist

- [x] SSL/HTTPS enabled
- [ ] Đổi `SECRET_KEY` trong `.env`
- [ ] Đổi `DATABASE_PASSWORD` trong `.env`
- [ ] Cấu hình `ZALO_APP_ID` và `ZALO_OA_SECRET_KEY`
- [ ] Enable UFW firewall
- [ ] Test webhook với Zalo
