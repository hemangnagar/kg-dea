#!/usr/bin/env bash
# Install the IntelDoc KG workbench on an Ubuntu host as a systemd service behind nginx.
# Usage (as root):  DOMAIN=kg.hemangnagar.dev bash deploy/install.sh
# Re-running is safe: it updates the checkout, keeps the corpus, and restarts the service.
set -euo pipefail
DOMAIN="${DOMAIN:?set DOMAIN, e.g. DOMAIN=kg.hemangnagar.dev}"
APP_DIR="${APP_DIR:-/opt/inteldoc}"
APP_USER="${APP_USER:-inteldoc}"
REPO="${REPO:-https://github.com/hemangnagar/kg-dea.git}"
BRANCH="${BRANCH:-main}"
PORT="${PORT:-8000}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q python3 python3-venv python3-pip git unzip nginx apache2-utils
id "$APP_USER" >/dev/null 2>&1 || useradd --system --no-create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
# The checkout is the user's home. Create it empty (no skeleton files) so that git clone accepts it.
if [[ ! -d "$APP_DIR/.git" ]]; then
  if [[ -d "$APP_DIR" ]] && [[ -n "$(ls -A "$APP_DIR")" ]]; then
    echo "$APP_DIR exists and is not a git checkout; move it aside and re-run." >&2; exit 1
  fi
  install -d -o "$APP_USER" -g "$APP_USER" "$APP_DIR"
fi

if [[ -d "$APP_DIR/.git" ]]; then
  sudo -u "$APP_USER" git -C "$APP_DIR" fetch -q origin "$BRANCH"
  sudo -u "$APP_USER" git -C "$APP_DIR" checkout -q "$BRANCH"
  sudo -u "$APP_USER" git -C "$APP_DIR" reset -q --hard "origin/$BRANCH"
else
  sudo -u "$APP_USER" git clone -q --branch "$BRANCH" "$REPO" "$APP_DIR"
fi
sudo -u "$APP_USER" bash "$APP_DIR/scripts/setup.sh"

sed -e "s|@APP_DIR@|$APP_DIR|g" -e "s|@APP_USER@|$APP_USER|g" -e "s|@PORT@|$PORT|g" "$APP_DIR/deploy/inteldoc.service" > /etc/systemd/system/inteldoc.service
systemctl daemon-reload
systemctl enable --now inteldoc
systemctl restart inteldoc

sed -e "s|@DOMAIN@|$DOMAIN|g" -e "s|@PORT@|$PORT|g" "$APP_DIR/deploy/nginx-inteldoc.conf" > /etc/nginx/sites-available/inteldoc
ln -sf /etc/nginx/sites-available/inteldoc /etc/nginx/sites-enabled/inteldoc
rm -f /etc/nginx/sites-enabled/default   # the app site is the default server, so every hostname and the bare IP get basic auth
if [[ ! -f /etc/nginx/inteldoc.htpasswd ]]; then
  echo "No /etc/nginx/inteldoc.htpasswd yet: create the demo login with  htpasswd -c /etc/nginx/inteldoc.htpasswd demo" >&2
  htpasswd -cb /etc/nginx/inteldoc.htpasswd demo "$(openssl rand -base64 18 | tee /root/inteldoc-demo-password.txt)"
  echo "Generated a password for user 'demo' in /root/inteldoc-demo-password.txt" >&2
fi
nginx -t && systemctl reload nginx

for i in $(seq 1 30); do curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null && break; sleep 1; done
curl -s "http://127.0.0.1:$PORT/api/health"; echo
echo "Service up. Next: issue the certificate with  certbot --nginx -d $DOMAIN  (see deploy/README.md)."
