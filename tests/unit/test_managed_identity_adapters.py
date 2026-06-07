from __future__ import annotations

from vtn_ai.foundry import OpenAIChatClient, OpenAIEmbeddingClient
from vtn_transcript.providers import AzureSpeechProvider
from vtn_visual.ocr import AzureVisionOcrProvider


def test_openai_clients_build_bearer_token_provider_from_token() -> None:
    chat = OpenAIChatClient(endpoint="https://example.openai.azure.com", token="token")
    embedding = OpenAIEmbeddingClient(endpoint="https://example.openai.azure.com", token="token")

    chat_provider = chat._azure_ad_token_provider()
    embedding_provider = embedding._azure_ad_token_provider()

    assert chat_provider is not None
    assert chat_provider() == "token"
    assert embedding_provider is not None
    assert embedding_provider() == "token"


def test_speech_provider_uses_bearer_token_header_when_token_auth() -> None:
    provider = AzureSpeechProvider(region="eastus", audio_path="audio.wav", token="speech-token")

    headers = provider._auth_headers()

    assert headers == {"Authorization": "Bearer speech-token"}


def test_vision_provider_uses_bearer_token_header_when_token_auth() -> None:
    provider = AzureVisionOcrProvider(endpoint="https://vision.example", token="vision-token")

    headers = provider._auth_headers()

    assert headers == {"Authorization": "Bearer vision-token"}
