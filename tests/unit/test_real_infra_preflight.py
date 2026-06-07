from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_preflight_module():
    path = Path(__file__).resolve().parents[1] / "infra" / "preflight_real_infra.py"
    spec = importlib.util.spec_from_file_location("preflight_real_infra", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pre_up_rejects_non_bcrypt_password_hash_without_plain_password() -> None:
    preflight = _load_preflight_module()

    result = preflight.validate_values(
        {
            "AZURE_SUBSCRIPTION_ID": "sub",
            "AZURE_LOCATION": "australiaeast",
            "POSTGRES_ADMIN_PASSWORD": "strong-password",
            "VTN_PASSWORD_HASH": "$argon2id$v=19$m=65536,t=3,p=4$preview$previewhash",
        },
        phase="pre-up",
    )

    assert not result.ok
    assert any("VTN_PASSWORD" in message for message in result.errors)


def test_pre_up_accepts_plain_password_without_hash() -> None:
    preflight = _load_preflight_module()

    result = preflight.validate_values(
        {
            "AZURE_SUBSCRIPTION_ID": "sub",
            "AZURE_LOCATION": "australiaeast",
            "POSTGRES_ADMIN_PASSWORD": "strong-password",
            "VTN_PASSWORD": "shared-password",
        },
        phase="pre-up",
    )

    assert result.ok


def test_final_phase_requires_service_bus_connection_details() -> None:
    preflight = _load_preflight_module()

    result = preflight.validate_values(
        {
            "AZURE_SUBSCRIPTION_ID": "sub",
            "AZURE_LOCATION": "australiaeast",
            "POSTGRES_ADMIN_PASSWORD": "strong-password",
            "VTN_PASSWORD": "shared-password",
        },
        phase="final",
    )

    assert not result.ok
    assert any("Service Bus" in message for message in result.errors)
