#!/bin/bash

# Скрипт для настройки SSL сертификатов с Let's Encrypt

set -e

DOMAIN=${1:-"your-domain.com"}
EMAIL=${2:-"admin@$DOMAIN"}

echo "🔒 Настройка SSL сертификатов для домена: $DOMAIN"

# Проверяем наличие certbot
if ! command -v certbot &> /dev/null; then
    echo "📦 Устанавливаем certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# Создаем папку для SSL
mkdir -p ssl

# Останавливаем nginx если запущен
echo "🛑 Останавливаем nginx для получения сертификата..."
docker-compose stop nginx || true

# Получаем сертификат
echo "📜 Получаем SSL сертификат от Let's Encrypt..."
sudo certbot certonly --standalone \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Копируем сертификаты
echo "📋 Копируем сертификаты..."
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*.pem

# Обновляем конфигурацию nginx
echo "⚙️ Обновляем конфигурацию nginx..."
sed -i "s/your-domain.com/$DOMAIN/g" nginx.conf
sed -i 's/# server {/server {/' nginx.conf
sed -i 's/# }/}/' nginx.conf
sed -i 's/# //' nginx.conf

# Добавляем HTTP -> HTTPS редирект
cat > nginx-ssl.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream app {
        server ifc-converter:5000;
    }

    # HTTP сервер (редирект на HTTPS)
    server {
        listen 80;
        server_name $DOMAIN;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://\$server_name\$request_uri;
        }
    }

    # HTTPS сервер
    server {
        listen 443 ssl http2;
        server_name $DOMAIN;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # SSL настройки
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Безопасность
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;

        client_max_body_size 100M;

        location / {
            proxy_pass http://app;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;

            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }
    }
}
EOF

mv nginx-ssl.conf nginx.conf

# Добавляем автообновление сертификатов
echo "🔄 Настраиваем автообновление сертификатов..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet && docker-compose restart nginx") | crontab -

# Запускаем сервисы
echo "🚀 Запускаем сервисы с SSL..."
docker-compose up -d

echo "✅ SSL настроен успешно!"
echo "🌐 Сайт доступен по адресу: https://$DOMAIN"
echo ""
echo "📋 Автообновление сертификатов настроено в crontab"
echo "📋 Проверить статус: sudo certbot certificates"