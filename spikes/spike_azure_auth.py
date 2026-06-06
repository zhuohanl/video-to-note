from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime

from azure.identity import DefaultAzureCredential

REQUIRED_ENV = [
    "AZURE_RESOURCE_GROUP",
    "AZURE_STORAGE_ACCOUNT",
    "AZURE_SERVICEBUS_NAMESPACE",
    "AZURE_FOUNDRY_RESOURCE",
]


def _run_az(command: list[str]) -> str:
    executable = shutil.which("az")
    if executable is None:
        msg = "Azure CLI is required for the liveness checks"
        raise RuntimeError(msg)

    completed = subprocess.run(
        [executable, *command],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return completed.stdout.strip()


def _require_env() -> dict[str, str]:
    values = {name: os.environ.get(name, "") for name in REQUIRED_ENV}
    missing = [name for name, value in values.items() if not value]
    if missing:
        msg = "Missing required real-infra env vars: " + ", ".join(missing)
        raise RuntimeError(msg)
    return values


def main() -> int:
    if os.environ.get("RUN_REAL") != "1":
        print("SKIP: set RUN_REAL=1 to run Azure credential/liveness checks")
        return 0

    credential = DefaultAzureCredential()
    token = credential.get_token("https://management.azure.com/.default")
    expires_at = datetime.fromtimestamp(token.expires_on, tz=UTC).isoformat()

    env = _require_env()
    account = json.loads(_run_az(["account", "show", "--output", "json"]))
    storage = _run_az(
        [
            "storage",
            "container",
            "list",
            "--auth-mode",
            "login",
            "--account-name",
            env["AZURE_STORAGE_ACCOUNT"],
            "--query",
            "[].name",
            "--output",
            "json",
        ]
    )
    servicebus = _run_az(
        [
            "servicebus",
            "queue",
            "list",
            "--resource-group",
            env["AZURE_RESOURCE_GROUP"],
            "--namespace-name",
            env["AZURE_SERVICEBUS_NAMESPACE"],
            "--query",
            "[].name",
            "--output",
            "json",
        ]
    )
    foundry = _run_az(
        [
            "resource",
            "show",
            "--resource-group",
            env["AZURE_RESOURCE_GROUP"],
            "--name",
            env["AZURE_FOUNDRY_RESOURCE"],
            "--query",
            "{id:id,type:type,location:location}",
            "--output",
            "json",
        ]
    )

    print(
        json.dumps(
            {
                "credential": "DefaultAzureCredential",
                "token_expires_at": expires_at,
                "subscription": account.get("id"),
                "tenant": account.get("tenantId"),
                "storage_containers": json.loads(storage),
                "servicebus_queues": json.loads(servicebus),
                "foundry_resource": json.loads(foundry),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
