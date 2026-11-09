# IntelDoc KG workbench: server requirements

Request to the server team (Tom) for hosting the knowledge-graph demo website. The application is a small Python web app that serves a pre-generated synthetic corpus. It needs no database server, no GPU, no model API access and no outbound network at runtime.

## 1. What we need from the server

### Machine

| Item | Requirement |
|---|---|
| Operating system | Linux, 64-bit (Ubuntu 22.04 or 24.04, or RHEL/Rocky 9) |
| CPU | 2 vCPU |
| Memory | 4 GB |
| Disk | 10 GB free on the volume holding the checkout (the data is about 300 MB; the rest is headroom for logs and a rebuild) |
| GPU | none |

### Software installed on the machine

| Item | Requirement |
|---|---|
| Python | 3.12 or newer, with `venv` and `pip` |
| Tools | `git`, `unzip`, `sha256sum` (coreutils), `curl` |
| Reverse proxy | nginx (or the site's standard proxy) in front of the app |
| Service manager | systemd (we provide the unit file) |

### Accounts and access

| Item | Requirement |
|---|---|
| Service account | a non-root user (for example `inteldoc`) with a home directory, to own the checkout and run the service |
| Our access | SSH access for the person deploying, with sudo for the one-time package install and the systemd and nginx configuration, or a Tom-run install from the steps we provide |
| Repository access | the server must be able to clone `https://github.com/hemangnagar/kg-dea` (private repository: a read-only deploy key or token), or we deliver the repository as a tarball |

### Network

| Item | Requirement |
|---|---|
| Outbound, install time only | HTTPS to `github.com`, `pypi.org` and `files.pythonhosted.org`. If egress is blocked, tell us and we will ship a wheelhouse with the tarball |
| Outbound, runtime | none |
| Inbound | HTTPS on 443 to the reverse proxy; the app itself listens on `127.0.0.1:8000` and must not be exposed directly |
| DNS | a hostname for the site (for example `inteldoc.<domain>`) |
| TLS | a certificate for that hostname; an internal CA is fine |
| Reachability | who may reach the site (VPN only, an IP allowlist, or the site's SSO gateway) |

### Authentication

The application has no login of its own. The "persona" switch in the interface is a demonstration control, not access control. Access must be enforced in front of it:

- SSO at the reverse proxy (preferred: the site's standard gateway, or nginx `auth_request`), or
- HTTP basic authentication at the proxy with credentials held by the demo team.

### Data handling

All content is synthetic: every organization, person, company and document is fictional, and the phone labels are deliberately non-dialable. The interface displays classification-style markings (U//FOUO, S//NF, U//LES) as part of the demonstration. The site should be treated as internal-only so that a casual viewer cannot mistake the markings for real material.

## 2. What we provide

- The repository, including the pre-generated 5,000-document corpus as a verified archive, the world data and the call-record generator.
- An install script (`bash scripts/setup.sh`, two to three minutes) and a start script (`bash scripts/start.sh`).
- A systemd unit file and an nginx server block for the hostname and certificate paths Tom gives us.
- A smoke-test checklist: the health endpoint, the expected counts on the first page, and the presenter's runbook.

## 3. Installation summary, for planning

```sh
sudo -u inteldoc git clone https://github.com/hemangnagar/kg-dea.git /opt/inteldoc
cd /opt/inteldoc && sudo -u inteldoc bash scripts/setup.sh
sudo systemctl enable --now inteldoc        # unit provided by us; runs scripts/start.sh on 127.0.0.1:8000
curl http://127.0.0.1:8000/api/health        # expect {"status":"ok","validated":5000,...}
```

## 4. Questions for Tom

1. Hostname and certificate: what name will the site have, and who issues the certificate?
2. Authentication: which mechanism will sit in front of it (SSO gateway, nginx auth, basic auth)?
3. Reachability: VPN only, allowlist, or open to the internal network?
4. Install path and service account name, if different from `/opt/inteldoc` and `inteldoc`.
5. Egress at install time: allowed to GitHub and PyPI, or should we deliver a tarball with a wheelhouse?
6. Who will run the install: our deployer over SSH, or Tom from our steps?
7. Logging and monitoring: where should service logs go, and is there a standard uptime check to register the health endpoint with?
8. Ports: is 8000 free on loopback, or should the service use another port?
9. Change control: is there a maintenance window or approval needed to add a new internal site?
