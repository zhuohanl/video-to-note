# Deploy Video-to-Note v2

Deployment uses Azure Developer CLI (`azd`) as the operator-facing lifecycle.

## Prerequisites

- Azure CLI and Azure Developer CLI installed.
- An Azure subscription with capacity for Container Apps, PostgreSQL Flexible Server, Storage, Service Bus, Key Vault, Application Insights, and Azure AI services.
- `uv`, `pnpm`, Docker, and Bash available locally.

## Configure an environment

```bash
az login
azd env new vtn-dev --subscription <subscription-id> --location <azure-region>
azd env set VTN_USERNAME local
azd env set VTN_PASSWORD '<shared-password>'
azd env set POSTGRES_ADMIN_PASSWORD '<strong-postgres-admin-password>'
```

`infra/hooks/seed_secrets.sh` hashes `VTN_PASSWORD`, generates `VTN_COOKIE_SECRET` if missing, and writes the runtime auth secrets to Key Vault. Apps receive secrets through Managed Identity and Key Vault references.

## Provision, deploy, and migrate

```bash
azd up --no-prompt
```

`azd up` provisions the Bicep resources, deploys the web/API/worker containers, seeds Key Vault secrets after provisioning, and applies Alembic migrations after deployment.

## Tear down

```bash
azd down --purge --force
```

This removes the environment resources. `--purge` is required so soft-deleted Key Vault and AI resources do not block recreation.

## Real lifecycle test

The real lifecycle test is opt-in because it creates paid Azure resources:

```bash
RUN_REAL=1 bash tests/infra/test_lifecycle.sh
```

The script runs `azd up`, checks `GET /healthz`, checks `POST /login`, runs `azd down --purge --force`, and verifies the resource group is gone.
