from __future__ import annotations

import os

import pytest
from vtn_ai.foundry import (
    FoundryChatModel,
    FoundryEmbeddingModel,
    OpenAIChatClient,
    OpenAIEmbeddingClient,
)


@pytest.mark.real_infra
def test_llm_real_foundry_json_and_embeddings() -> None:
    required = (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
        "AZURE_OPENAI_EMBED_DEPLOYMENT",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        pytest.skip(f"missing Azure OpenAI env vars: {', '.join(missing)}")

    chat = FoundryChatModel(
        client=OpenAIChatClient(
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
        ),
        deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
    )
    payload = chat.complete_json(
        "Return a JSON object with keys title and summary for a tiny video outline.",
        schema={"type": "object"},
    )
    assert isinstance(payload.get("title"), str)
    assert isinstance(payload.get("summary"), str)

    embeddings = FoundryEmbeddingModel(
        client=OpenAIEmbeddingClient(
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
        ),
        deployment=os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"],
    ).embed(["first section", "second section"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) > 0
    assert len(embeddings[0]) == len(embeddings[1])
