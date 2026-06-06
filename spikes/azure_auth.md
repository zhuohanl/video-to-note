# Azure Auth Spike

Date: 2026-06-06
Status: blocked for real liveness until target resource names are supplied.

## Contract Locked

- Local real-infra checks use `DefaultAzureCredential` and Azure CLI login against the intended subscription.
- Cloud services use Managed Identity through the same `DefaultAzureCredential` chain.
- No `[TEST-E2E-REAL]` or deploy acceptance task may run until `RUN_REAL=1 uv run python spikes/spike_azure_auth.py` succeeds.

## Required Environment

- `AZURE_RESOURCE_GROUP`
- `AZURE_STORAGE_ACCOUNT`
- `AZURE_SERVICEBUS_NAMESPACE`
- `AZURE_FOUNDRY_RESOURCE`

## RBAC Roles

Minimum expected roles for the signed-in identity or managed identity:

- Contributor on the target resource group.
- Storage Blob Data Contributor on the storage account.
- Azure Service Bus Data Owner or Azure Service Bus Data Sender/Receiver as appropriate for queue tests.
- Cognitive Services OpenAI User or equivalent model-invocation role for Azure AI Foundry deployments.
- Key Vault Secrets User for runtime secret reads; Key Vault Secrets Officer for provisioning hooks that seed secrets.

## Observed Local Tooling

- Azure CLI is installed and `az account show` succeeds.
- Azure Developer CLI is installed.
- Target resource names are not yet present in environment variables, so live liveness cannot be completed defensibly.
