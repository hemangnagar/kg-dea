#!/usr/bin/env bash
# Write the nginx site for the workbench. HTTPS when a certificate from deploy/tls-alpn.sh (or certbot copied to the
# same paths) exists under /etc/ssl/inteldoc, plain HTTP otherwise. The app does its own password login, so nginx
# only terminates TLS and proxies. Usage (as root): DOMAIN=host.example.com [PORT=8000] bash deploy/render-nginx.sh
set -euo pipefail
HOST="${DOMAIN:?set DOMAIN}"
PORT="${PORT:-8000}"
SITE=/etc/nginx/sites-available/inteldoc
PROXY="    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }"
if [[ -s /etc/ssl/inteldoc/fullchain.pem && -s /etc/ssl/inteldoc/key.pem ]]; then
cat > "$SITE" <<EOF
# IntelDoc KG workbench: TLS termination and reverse proxy. The app handles the password login itself.
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $HOST;
    return 301 https://\$host\$request_uri;
}
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name $HOST;
    ssl_certificate /etc/ssl/inteldoc/fullchain.pem;
    ssl_certificate_key /etc/ssl/inteldoc/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
$PROXY
}
EOF
else
cat > "$SITE" <<EOF
# IntelDoc KG workbench: reverse proxy. The app handles the password login itself.
# Add HTTPS with  DOMAIN=$HOST bash deploy/tls-alpn.sh  (port 443 only) or  certbot --nginx -d $HOST  (needs port 80).
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $HOST;
$PROXY
}
EOF
fi
ln -sf "$SITE" /etc/nginx/sites-enabled/inteldoc
rm -f /etc/nginx/sites-enabled/default
nginx -t
