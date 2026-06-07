# P6 Final Acceptance Record

Status: pending

Use this template to create `docs/acceptance.md` only after the opt-in real
Azure acceptance run has completed. Do not treat this template as final evidence.

## Environment

- Date:
- Operator:
- Azure subscription:
- Azure location:
- azd environment:
- Resource group:
- API URL:
- Web URL:

## Preconditions

- `az account show` confirms the target subscription.
- `azd env get-values` includes `AZURE_SUBSCRIPTION_ID`, `AZURE_LOCATION`,
  `POSTGRES_ADMIN_PASSWORD`, and either `VTN_PASSWORD` or a bcrypt
  `VTN_PASSWORD_HASH`.
- Live Service Bus details are available through
  `AZURE_SERVICE_BUS_CONNECTION_STRING` or
  `AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE` after provisioning.
- The operator accepts that the run creates paid Azure resources.

## Commands

```bash
uv run python tests/infra/preflight_real_infra.py --phase pre-up
RUN_REAL=1 bash tests/infra/test_lifecycle.sh
uv run pytest -m real_infra
azd down --purge --force
```

`tests/infra/test_lifecycle.sh` runs `azd up`, validates the deployed API,
runs the deployed API journey, runs the deployed browser journey, runs `azd down
--purge --force`, and verifies the resource group was removed.

## Results

- `azd up`:
- Deployed API journey:
- Deployed browser journey:
- Full real Service Bus journey:
- `uv run pytest -m real_infra`:
- `azd down --purge --force`:
- Resource group deletion check:
- CI run:

## Independent Reviewer

- Independent reviewer pass:
- Reviewer:
- Review date:
- Verdict:
- Findings:
