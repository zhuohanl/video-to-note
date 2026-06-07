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
  `POSTGRES_ADMIN_PASSWORD`, and `VTN_PASSWORD`; the seed hook may derive the
  bcrypt `VTN_PASSWORD_HASH`.
- Live Service Bus details are available through
  `AZURE_SERVICE_BUS_CONNECTION_STRING` or
  `AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE` after provisioning.
- Full-suite adapter inputs are set: `DATABASE_URL`, `VTN_PASSWORD_HASH`,
  `VTN_COOKIE_SECRET`, Azure OpenAI endpoint/key/deployments, Azure Speech
  key/region/audio fixture path, and Azure Vision endpoint/key/frame fixture
  path.
- The operator accepts that the run creates paid Azure resources.

## Commands

```bash
uv run python tests/infra/preflight_real_infra.py --phase pre-up
RUN_REAL=1 bash tests/infra/test_lifecycle.sh
```

`tests/infra/test_lifecycle.sh` runs `azd up`, validates the deployed API, runs
`preflight_real_infra.py --phase final`, runs `uv run pytest -m real_infra`,
runs the deployed browser journey, runs `azd down --purge --force`, and verifies
the resource group was removed.

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
