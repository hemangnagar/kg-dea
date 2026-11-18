# IntelDoc KG workbench: Azure container deployment

Request to the server team (Tom) for hosting the knowledge-graph demo website as a container on Azure. The application is a small Python web app that serves a pre-generated synthetic corpus. We deliver one self-contained image (about 400 MB) that needs no database, no GPU, no model API and no outbound network at runtime.

**Recommended service: Azure Container Apps.** It provides the three things a bare container cannot: HTTPS with a managed certificate, a hostname, and sign-in with Microsoft Entra ID at the ingress. The application has no login of its own, so the Entra ID sign-in at the ingress is what makes the site safe to expose.

## 1. What we need from the server team

| Item | Requirement |
|---|---|
| 1. Subscription and resource group | a resource group for the demo, in the region the audience is in, with our deployer granted Contributor on that group |
| 2. Container registry | an Azure Container Registry (Basic tier is enough) that we can push to, or permission to create one in the group. We build the image in the registry with `az acr build`, so nothing needs Docker locally |
| 3. Container Apps environment | an Azure Container Apps environment (consumption plan) in the group, or permission to create one. One app, 1 vCPU, 2 GB memory, one replica |
| 4. Sign-in | an Entra ID app registration for the site, or permission for us to create one, so that Container Apps authentication ("Easy Auth") requires a Microsoft login before any request reaches the app. If only certain people may view it, the group or users to allow |
| 5. Hostname and certificate | either the default `*.azurecontainerapps.io` hostname (works immediately, managed certificate) or a custom name under the site's domain, in which case a DNS record and a certificate, which Container Apps can also manage |
| 6. Reachability | whether the ingress may be public (protected by sign-in) or must be restricted by IP allowlist or VNet. Public ingress with Entra ID sign-in is the simplest and is what we recommend for a demo |
| 7. Logging | a Log Analytics workspace for the environment, or permission to create one |

Nothing else is required. The image is built from the repository, contains the corpus and the partner call records, and makes no outbound requests once running.

## 2. What we provide

- The repository with a `Dockerfile`, a `compose.yaml` for local runs, and the published 5,000-document corpus archive that the build verifies and unpacks.
- The image, built in the registry: `az acr build --registry <acr> --image inteldoc:1.0 .`
- The Container App definition (image, target port 8000, external ingress, one replica, health probe on `/api/health`).
- The Entra ID authentication configuration, the smoke test, and the presenter's runbook.

## 3. Deployment sketch, for planning

The exact flags should be confirmed against the current Azure CLI when we run them; this is the shape of the work, about an hour once items 1 to 4 exist.

```sh
az acr build --registry <acr> --image inteldoc:1.0 .
az containerapp create --name inteldoc --resource-group <rg> --environment <env> \
  --image <acr>.azurecr.io/inteldoc:1.0 --registry-server <acr>.azurecr.io \
  --target-port 8000 --ingress external --min-replicas 1 --max-replicas 1 --cpu 1 --memory 2Gi
az containerapp auth microsoft update --name inteldoc --resource-group <rg> \
  --client-id <app-registration-id> --tenant-id <tenant> --client-secret <secret>
az containerapp auth update --name inteldoc --resource-group <rg> --unauthenticated-client-action RedirectToLoginPage
```

Smoke test: `https://<hostname>/api/health` returns `{"status":"ok","validated":5000,...}` after sign-in, and the first page shows 5,000 cables, 958 entities and 15,041 facts at Secret // NOFORN.

## 4. Questions for Tom

1. Which subscription and region, and can a resource group be created for the demo with Contributor for our deployer?
2. Is there an existing Container Registry and Container Apps environment to use, or do we create them in the group?
3. Entra ID: can we create the app registration ourselves, or does the identity team create it? Who may sign in: everyone in the tenant, or a group?
4. Hostname: the default Container Apps name, or a custom one under the site's domain?
5. Ingress: public behind sign-in, or restricted by IP or VNet?
6. Any change-control step, cost approval or tagging policy for a new resource group?

## 5. Data handling

All content is synthetic: every organization, person, company and document is fictional, and the phone labels are deliberately non-dialable. The interface displays classification-style markings (U//FOUO, S//NF, U//LES) as part of the demonstration. Sign-in at the ingress keeps the site internal so that a casual viewer cannot mistake the markings for real material.

## Alternatives, if Container Apps is not available

- **Azure App Service for Containers** works the same way: same image, built-in authentication with Entra ID, managed certificate. Use the B1 or higher plan.
- **A VM with root access** (any Linux, 2 vCPU, 4 GB, 10 GB disk): we install Python, nginx and the service ourselves; the server team provides the VM, a hostname with a certificate, the network path and an SSO front end or permission to run basic authentication. This was the earlier plan and remains workable.
