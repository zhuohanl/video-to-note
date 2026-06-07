from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import NamedTuple

BCRYPT_RE = re.compile(r"^\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}$")
SERVICE_BUS_KEYS = (
    "AZURE_SERVICE_BUS_CONNECTION_STRING",
    "AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE",
)
PRE_UP_REQUIRED_KEYS = (
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_LOCATION",
    "POSTGRES_ADMIN_PASSWORD",
)
POST_UP_REQUIRED_KEYS = (
    "API_URL",
    "WEB_URL",
)
FINAL_PHASES = {"post-up", "servicebus", "final"}
COMMAND_SUFFIXES = ("", ".cmd", ".exe")


class ValidationResult(NamedTuple):
    ok: bool
    errors: list[str]
    warnings: list[str]


def parse_azd_env_values(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        if not key.isidentifier() or not key.isupper():
            continue
        try:
            parsed = shlex.split(raw_value, posix=True)
        except ValueError:
            parsed = []
        values[key] = parsed[0] if parsed else raw_value.strip().strip('"')
    return values


def _resolve_command(name: str) -> str:
    for suffix in COMMAND_SUFFIXES:
        command = shutil.which(f"{name}{suffix}")
        if command:
            return command
    raise RuntimeError(f"{name} is required on PATH for real-infra preflight.")


def load_azd_env_values() -> dict[str, str]:
    azd = _resolve_command("azd")
    completed = subprocess.run(
        [azd, "env", "get-values"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"azd env get-values failed: {message}")
    return parse_azd_env_values(completed.stdout)


def _has_usable_auth_secret(values: dict[str, str]) -> bool:
    if values.get("VTN_PASSWORD"):
        return True
    password_hash = values.get("VTN_PASSWORD_HASH", "")
    return bool(BCRYPT_RE.match(password_hash))


def validate_values(values: dict[str, str], *, phase: str) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    for key in PRE_UP_REQUIRED_KEYS:
        if not values.get(key):
            errors.append(
                f"Missing {key}; set it with azd env set before running real infrastructure."
            )

    if not _has_usable_auth_secret(values):
        errors.append(
            "Set VTN_PASSWORD or a bcrypt VTN_PASSWORD_HASH before running real infrastructure; "
            "the API login path validates bcrypt hashes."
        )

    if phase in FINAL_PHASES:
        for key in POST_UP_REQUIRED_KEYS:
            if not values.get(key):
                errors.append(
                    f"Missing {key}; run this phase after azd up has written deployment outputs."
                )
        if not any(values.get(key) for key in SERVICE_BUS_KEYS):
            errors.append(
                "Missing Service Bus connection details; set AZURE_SERVICE_BUS_CONNECTION_STRING "
                "or AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE for the live Service Bus tests."
            )

    if values.get("VTN_PASSWORD_HASH", "").startswith("$argon2"):
        warnings.append(
            "VTN_PASSWORD_HASH is argon2-formatted and cannot satisfy the bcrypt login path."
        )

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _check_az_login() -> str | None:
    try:
        az = _resolve_command("az")
    except RuntimeError as exc:
        return str(exc)
    completed = subprocess.run(
        [az, "account", "show"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return None
    message = completed.stderr.strip() or completed.stdout.strip()
    return f"Azure CLI is not logged in or cannot read the active account: {message}"


def _merged_values() -> dict[str, str]:
    values = load_azd_env_values()
    values.update({key: value for key, value in os.environ.items() if value})
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate prerequisites for opt-in real Azure acceptance runs."
    )
    parser.add_argument(
        "--phase",
        choices=("pre-up", "post-up", "servicebus", "final"),
        default="pre-up",
        help="Validation phase. pre-up is safe to run before resource creation.",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []
    az_error = _check_az_login()
    if az_error:
        errors.append(az_error)

    try:
        values = _merged_values()
    except RuntimeError as exc:
        errors.append(str(exc))
        values = {}

    result = validate_values(values, phase=args.phase)
    errors.extend(result.errors)

    for warning in result.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    if errors:
        print("Real-infra preflight failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Real-infra preflight passed for phase {args.phase}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
