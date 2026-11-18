# Deploying on your own server (hemangnagar.dev)

Two ways, matching how other sites on the box are run. Both put the app on `127.0.0.1:8000` and a reverse proxy with HTTP basic authentication in front of it; the app has no login of its own.

## A. systemd service behind nginx (if the other sites run as services)

1. DNS: add an A (and AAAA if used) record for the subdomain, e.g. `kg.hemangnagar.dev`, pointing at the server.
2. As root on the server:

```sh
git clone https://github.com/hemangnagar/kg-dea.git /tmp/kg-dea && DOMAIN=kg.hemangnagar.dev bash /tmp/kg-dea/deploy/install.sh
```

   This installs packages, creates the `inteldoc` user, clones to `/opt/inteldoc`, runs `scripts/setup.sh` (unpacks the corpus and generates the call records, two to three minutes), installs and starts the systemd service, installs the nginx site with basic auth, and generates a password for user `demo` in `/root/inteldoc-demo-password.txt`. Change it with `htpasswd /etc/nginx/inteldoc.htpasswd demo`.
3. HTTPS: `certbot --nginx -d kg.hemangnagar.dev` (install certbot first if the box does not have it: `apt-get install -y certbot python3-certbot-nginx`).
4. Check: `https://kg.hemangnagar.dev/api/health` after the basic-auth prompt returns `{"status":"ok","validated":5000,...}`; the first page shows 5,000 cables, 958 entities, 15,041 facts at Secret // NOFORN.

Update later with the same command; it keeps the corpus and restarts the service. Logs: `journalctl -u inteldoc -f`.

## B. docker compose behind an existing proxy (if the other sites run in containers)

```sh
git clone https://github.com/hemangnagar/kg-dea.git /opt/inteldoc && cd /opt/inteldoc
docker compose -f deploy/compose.yaml up -d --build
```

The build takes a few minutes the first time (it unpacks the corpus inside the image). Then add the subdomain to the existing reverse proxy pointing at `http://127.0.0.1:8000`, with basic auth and the usual certificate handling. Check `curl http://127.0.0.1:8000/api/health` on the box.

## Either way

- Resources: 1 vCPU, 2 GB memory, 1 GB of disk for the checkout and corpus (plus the image under B).
- No outbound traffic at runtime; no API keys on the server.
- All data is synthetic, but the interface shows classification-style markings, so keep basic auth on and do not link the site publicly.
- The presenter's script is `docs/demo-runbook.md`; its numbers apply to this deployment unchanged.
