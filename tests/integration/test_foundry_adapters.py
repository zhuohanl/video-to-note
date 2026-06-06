from __future__ import annotations

from vtn_ai.foundry import FoundryChatModel, FoundryEmbeddingModel
from vtn_segment.detectors import SemanticShiftDetector


class FakeChatClient:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, **kwargs) -> str:
        self.calls += 1
        assert kwargs["response_format"] == {"type": "json_object"}
        if self.calls == 1:
            return "{not json"
        return '{"title": "Recovered", "summary": "Valid JSON after retry"}'


class FakeEmbeddingClient:
    def embed(self, *, model: str, input: list[str]) -> list[list[float]]:
        assert model == "embed-deployment"
        del input
        return [[1.0, 0.0], [0.0, 1.0]]


def test_foundry_chat_complete_json_retries_invalid_json() -> None:
    client = FakeChatClient()
    model = FoundryChatModel(client=client, deployment="chat-deployment")

    result = model.complete_json("Return JSON", schema={"type": "object"})

    assert result == {"title": "Recovered", "summary": "Valid JSON after retry"}
    assert client.calls == 2


def test_embedding_model_and_semantic_shift_detector() -> None:
    embedding_model = FoundryEmbeddingModel(
        client=FakeEmbeddingClient(),
        deployment="embed-deployment",
    )
    assert embedding_model.embed(["alpha", "beta"]) == [[1.0, 0.0], [0.0, 1.0]]

    detector = SemanticShiftDetector(embedding_model=embedding_model, threshold=0.1)
    candidates = detector.detect(["same topic", "different topic"])

    assert candidates
    assert candidates[0].signal_type == "semantic_shift"
