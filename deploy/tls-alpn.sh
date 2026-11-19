#!/usr/bin/env bash
# Issue a Let's Encrypt certificate for the workbench host over port 443 (tls-alpn-01) and enable HTTPS in nginx.
# For hosts where port 80 is closed, so certbot's http-01 challenge cannot run. Run as root after deploy/install.sh:
#   DOMAIN=kg.example.com bash deploy/tls-alpn.sh
# Renewal: acme.sh's cron job renews every 60 days; the pre/post hooks stop nginx for the few seconds the challenge needs port 443.
set -euo pipefail
HOST="${DOMAIN:?set DOMAIN, e.g. DOMAIN=kg.example.com}"
PORT="${PORT:-8000}"
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -q socat git >/dev/null
if [[ ! -x /root/.acme.sh/acme.sh ]]; then
  rm -rf /tmp/acme.sh
  git clone -q --depth 1 https://github.com/acmesh-official/acme.sh.git /tmp/acme.sh
  (cd /tmp/acme.sh && ./acme.sh --install --nocron --no-profile >/dev/null)
fi
ACME=/root/.acme.sh/acme.sh
"$ACME" --set-default-ca --server letsencrypt >/dev/null
systemctl stop nginx
if ! "$ACME" --issue --alpn -d "$HOST" --pre-hook "systemctl stop nginx" --post-hook "systemctl start nginx" --keylength ec-256 >/var/log/acme-issue.log 2>&1; then
  tail -n 20 /var/log/acme-issue.log
  systemctl start nginx
  exit 1
fi
systemctl start nginx
install -d -m 700 /etc/ssl/inteldoc
"$ACME" --install-cert --ecc -d "$HOST" --key-file /etc/ssl/inteldoc/key.pem --fullchain-file /etc/ssl/inteldoc/fullchain.pem --reloadcmd "systemctl reload nginx" >/dev/null
"$ACME" --install-cronjob >/dev/null

cat > /etc/nginx/sites-available/inteldoc <<EOF
# IntelDoc KG workbench behind nginx with HTTP basic authentication and TLS (acme.sh, tls-alpn-01).
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $HOST;
    return 301 https://\$host\$request_uri;
}
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    http2 on;
    server_name $HOST;
    ssl_certificate /etc/ssl/inteldoc/fullchain.pem;
    ssl_certificate_key /etc/ssl/inteldoc/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    auth_basic "IntelDoc KG demo (synthetic data)";
    auth_basic_user_file /etc/nginx/inteldoc.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
EOF
nginx -t && systemctl reload nginx

PW=$(cat /root/inteldoc-demo-password.txt)
echo "noauth=$(curl -s -o /dev/null -w '%{http_code}' "https://$HOST/")"
echo "auth=$(curl -s -o /dev/null -w '%{http_code}' -u "demo:$PW" "https://$HOST/")"
curl -s -u "demo:$PW" "https://$HOST/api/health"; echo
echo "cert: $(openssl s_client -connect 127.0.0.1:443 -servername "$HOST" </dev/null 2>/dev/null | openssl x509 -noout -enddate -issuer | tr '\n' ' ')"
echo "HTTPS is up at https://$HOST/ (user demo, password in /root/inteldoc-demo-password.txt)."
