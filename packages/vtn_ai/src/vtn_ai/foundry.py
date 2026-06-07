from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast

from openai import AzureOpenAI


class ChatClient(Protocol):
    def complete(self, **kwargs: object) -> str: ...


class EmbeddingClient(Protocol):
    def embed(self, *, model: str, input: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class OpenAIChatClient:
    endpoint: str
    api_key: str | None = None
    token: str | None = None
    api_version: str = "2024-10-21"

    def _azure_ad_token_provider(self) -> Callable[[], str] | None:
        if self.token is None:
            return None
        token = self.token
        return lambda: token

    def complete(self, **kwargs: object) -> str:
        token_provider = self._azure_ad_token_provider()
        client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            azure_ad_token_provider=token_provider,
            api_version=self.api_version,
        )
        response = client.chat.completions.create(**kwargs)  # type: ignore[call-overload]
        content = cast(str | None, response.choices[0].message.content)
        if content is None:
            raise ValueError("chat completion returned no content")
        return content


@dataclass(frozen=True)
class OpenAIEmbeddingClient:
    endpoint: str
    api_key: str | None = None
    token: str | None = None
    api_version: str = "2024-10-21"

    def _azure_ad_token_provider(self) -> Callable[[], str] | None:
        if self.token is None:
            return None
        token = self.token
        return lambda: token

    def embed(self, *, model: str, input: list[str]) -> list[list[float]]:
        token_provider = self._azure_ad_token_provider()
        client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            azure_ad_token_provider=token_provider,
            api_version=self.api_version,
        )
        response = client.embeddings.create(model=model, input=input)
        return [list(item.embedding) for item in response.data]


@dataclass(frozen=True)
class FoundryChatModel:
    client: ChatClient
    deployment: str
    temperature: float = 0.2
    max_retries: int = 1

    def complete_json(self, prompt: str, schema: dict[str, object] | None = None) -> dict[str, Any]:
        del schema
        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            content = self.client.complete(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                last_error = exc
                continue
            if not isinstance(parsed, dict):
                last_error = ValueError("chat completion JSON must be an object")
                continue
            return parsed
        raise ValueError("chat completion did not return valid JSON") from last_error


@dataclass(frozen=True)
class FoundryEmbeddingModel:
    client: EmbeddingClient
    deployment: str

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.client.embed(model=self.deployment, input=texts)
