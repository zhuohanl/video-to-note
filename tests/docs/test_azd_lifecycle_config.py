from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
PARAMETERS = ROOT / "infra" / "main.parameters.json"
COGNITIVE = ROOT / "infra" / "modules" / "cognitive.bicep"
APPS = ROOT / "infra" / "modules" / "apps.bicep"


def test_main_parameters_use_env_for_login_and_openai_deployments() -> None:
    parameters = json.loads(PARAMETERS.read_text())["parameters"]

    assert parameters["loginUsername"]["value"] == "${VTN_USERNAME}"
    assert parameters["openAiChatDeploymentName"]["value"] == "${AZURE_OPENAI_CHAT_DEPLOYMENT}"
    assert parameters["openAiEmbedDeploymentName"]["value"] == "${AZURE_OPENAI_EMBED_DEPLOYMENT}"


def test_cognitive_module_declares_openai_model_deployments() -> None:
    text = COGNITIVE.read_text()

    assert "Microsoft.CognitiveServices/accounts/deployments@2024-10-01" in text
    assert "openAiChatDeploymentName" in text
    assert "openAiEmbedDeploymentName" in text
    assert "output openAiChatDeploymentName" in text
    assert "output openAiEmbedDeploymentName" in text


def test_apps_receive_openai_deployment_names_from_infra() -> None:
    text = APPS.read_text()

    assert "AZURE_OPENAI_CHAT_DEPLOYMENT" in text
    assert "AZURE_OPENAI_EMBED_DEPLOYMENT" in text
