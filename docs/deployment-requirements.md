# IntelDoc KG workbench: server requirements

Request to the server team (Tom) for hosting the knowledge-graph demo website. The application is a small Python web app that serves a pre-generated synthetic corpus. It needs no database server, no GPU, no model API access and no outbound network at runtime.

Two ways to host it are described below. **Option A, a VM with root access, is the preferred path**: it needs the least from the server team and gets us to a working site fastest. Option B, a container image, is the fallback if the site does not hand out root or runs everything on a container platform.

## Option A (preferred): a VM with root access

We install and operate everything on the machine ourselves. The server team provides four things.

| Item | Requirement |
|---|---|
| 1. The VM | Linux, 64-bit (Ubuntu 22.04 or 24.04, or RHEL/Rocky 9), 2 vCPU, 4 GB memory, 10 GB free disk, no GPU. Root (sudo) for our deployer over SSH. |
| 2. Hostname and TLS | a DNS name for the site (for example `inteldoc.<domain>`) and a certificate for it; an internal CA is fine. |
| 3. Network path | inbound HTTPS (443) to the VM from the intended audience (VPN only, an IP allowlist, or the internal network), and outbound HTTPS to `github.com`, `pypi.org` and `files.pythonhosted.org` during installation only. If egress is blocked we bring a tarball with the packages instead. No outbound traffic is needed at runtime. |
| 4. Authentication in front | the application has no login of its own, so access must be enforced before it: either the site's SSO gateway in front of the site, or permission for us to run HTTP basic authentication at the reverse proxy with credentials held by the demo team. |

Everything else is ours: Python 3.12, nginx as the reverse proxy on 443 forwarding to the app on `127.0.0.1:8000`, a systemd service, log rotation and OS patching while the demo is live.

### Installation summary, for planning

```sh
sudo -u inteldoc git clone https://github.com/hemangnagar/kg-dea.git /opt/inteldoc
cd /opt/inteldoc && sudo -u inteldoc bash scripts/setup.sh    # two to three minutes
sudo systemctl enable --now inteldoc                            # runs scripts/start.sh on 127.0.0.1:8000
curl http://127.0.0.1:8000/api/health                           # expect {"status":"ok","validated":5000,...}
```

### Questions for Tom (Option A)

1. Can a VM with root access for our deployer be provided, and by when?
2. Hostname and certificate: what name will the site have, and who issues the certificate?
3. Reachability: VPN only, allowlist, or open to the internal network?
4. Authentication: SSO gateway in front, or basic auth run by us?
5. Egress at install time: allowed to GitHub and PyPI, or should we bring a tarball?
6. Any change-control step or maintenance window for adding a new internal site?

## Option B (fallback): a container image

If root on a VM is not possible, we deliver a single container image with the application, the pre-generated corpus and the partner call records baked in (about 400 MB). It needs no network access at all, in or out, except the HTTP it serves.

| Item | Requirement |
|---|---|
| Container runtime | Docker or Podman on a host, or the site's container platform; tell us which, and how images are delivered (registry push or an image file) |
| Resources | 2 vCPU, 4 GB memory, 2 GB disk for the image |
| Hostname and TLS | as in Option A |
| Network path | inbound HTTPS to whatever terminates TLS in front of the container; the container listens on port 8000 and is not exposed directly |
| Authentication in front | as in Option A; if the site has no standard front end for containers, our image can include nginx with basic auth |

### Questions for Tom (Option B)

1. Which container runtime or platform, and how should the image be delivered?
2. Who runs the reverse proxy and TLS termination in front of containers?
3. Hostname, certificate, reachability and authentication, as for Option A.

## Data handling (both options)

All content is synthetic: every organization, person, company and document is fictional, and the phone labels are deliberately non-dialable. The interface displays classification-style markings (U//FOUO, S//NF, U//LES) as part of the demonstration. The site should be treated as internal-only so that a casual viewer cannot mistake the markings for real material.

## What we provide (both options)

- The repository, including the pre-generated 5,000-document corpus as a verified archive, the world data and the call-record generator.
- Install and start scripts, a systemd unit and an nginx server block (Option A), or the container image and a compose file (Option B).
- A smoke-test checklist: the health endpoint, the expected counts on the first page, and the presenter's runbook.
