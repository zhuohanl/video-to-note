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


def test_pre_up_rejects_hash_without_plain_password_for_login_smoke() -> None:
    preflight = _load_preflight_module()

    result = preflight.validate_values(
        {
            "AZURE_SUBSCRIPTION_ID": "sub",
            "AZURE_LOCATION": "australiaeast",
            "POSTGRES_ADMIN_PASSWORD": "strong-password",
            "VTN_PASSWORD_HASH": "$2b$12$abcdefghijklmnopqrstuu34n0xk5N/9cQZRqH9klU7QG6O9YtbkW",
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


def test_final_phase_requires_all_full_real_suite_prerequisites() -> None:
    preflight = _load_preflight_module()

    result = preflight.validate_values(
        {
            "AZURE_SUBSCRIPTION_ID": "sub",
            "AZURE_LOCATION": "australiaeast",
            "POSTGRES_ADMIN_PASSWORD": "strong-password",
            "VTN_PASSWORD": "shared-password",
            "API_URL": "https://api.example.test",
            "WEB_URL": "https://web.example.test",
            "AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE": "vtn-bus.servicebus.windows.net",
        },
        phase="final",
    )

    assert not result.ok
    assert any("AZURE_OPENAI_ENDPOINT" in message for message in result.errors)
    assert any("AZURE_SPEECH_REGION" in message for message in result.errors)
    assert any("DATABASE_URL" in message for message in result.errors)


def test_parse_azd_values_normalizes_bicep_output_names() -> None:
    preflight = _load_preflight_module()

    values = preflight.parse_azd_env_values(
        '\n'.join(
            [
                'apiUrl="https://api.example.test"',
                'webUrl="https://web.example.test"',
                'keyVaultName="vtn-kv"',
                'openAiEndpoint="https://openai.example.test"',
                'openAiChatDeploymentName="chat-deploy"',
                'openAiEmbedDeploymentName="embed-deploy"',
                'speechEndpoint="https://australiaeast.api.cognitive.microsoft.com/"',
                'visionEndpoint="https://vision.example.test"',
                'serviceBusNamespace="vtn-bus"',
            ]
        )
    )

    assert values["API_URL"] == "https://api.example.test"
    assert values["WEB_URL"] == "https://web.example.test"
    assert values["KEY_VAULT_NAME"] == "vtn-kv"
    assert values["AZURE_OPENAI_ENDPOINT"] == "https://openai.example.test"
    assert values["AZURE_OPENAI_CHAT_DEPLOYMENT"] == "chat-deploy"
    assert values["AZURE_OPENAI_EMBED_DEPLOYMENT"] == "embed-deploy"
    assert values["AZURE_SPEECH_ENDPOINT"] == "https://australiaeast.api.cognitive.microsoft.com/"
    assert values["AZURE_SPEECH_REGION"] == "australiaeast"
    assert values["AZURE_VISION_ENDPOINT"] == "https://vision.example.test"
    assert values["AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE"] == (
        "vtn-bus.servicebus.windows.net"
    )


def test_shell_exports_include_normalized_lifecycle_values() -> None:
    preflight = _load_preflight_module()

    exports = preflight.format_shell_exports(
        {
            "API_URL": "https://api.example.test",
            "WEB_URL": "https://web.example.test",
            "AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE": "vtn-bus.servicebus.windows.net",
            "ignored": "lowercase",
        }
    )

    assert "export API_URL=https://api.example.test" in exports
    assert "export WEB_URL=https://web.example.test" in exports
    assert (
        "export AZURE_SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE=vtn-bus.servicebus.windows.net"
        in exports
    )
    assert "ignored" not in exports
