from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

TRANSCRIPT_SAMPLE: list[dict[str, object]] = [
    {"start_sec": 0.0, "end_sec": 4.2, "speaker": "Speaker 1", "text": "Welcome to the session."},
    {
        "start_sec": 4.2,
        "end_sec": 10.0,
        "speaker": "Speaker 1",
        "text": "We will look at the architecture.",
    },
    {
        "start_sec": 10.0,
        "end_sec": 16.0,
        "speaker": "Speaker 1",
        "text": "The worker writes progress into the database.",
    },
    {
        "start_sec": 16.0,
        "end_sec": 22.0,
        "speaker": "Speaker 1",
        "text": "The API streams those events to the browser.",
    },
    {
        "start_sec": 22.0,
        "end_sec": 28.0,
        "speaker": "Speaker 1",
        "text": "Finally the note is reviewed and exported.",
    },
]

VISUAL_EVENTS_SAMPLE: list[dict[str, object]] = [
    {
        "at_sec": 1.0,
        "event_type": "slide",
        "phash": "8f1c2a3b4d5e6071",
        "ocr_text": "Architecture overview",
        "frame_uri": "local://frames/video-1/0001.png",
    },
    {
        "at_sec": 5.0,
        "event_type": "slide",
        "phash": "8f1c2a3b4d5e6070",
        "ocr_text": "Browser never calls worker",
        "frame_uri": "local://frames/video-1/0002.png",
    },
    {
        "at_sec": 9.0,
        "event_type": "demo",
        "phash": "1a2b3c4d5e6f7081",
        "ocr_text": "Submit job",
        "frame_uri": "local://frames/video-1/0003.png",
    },
    {
        "at_sec": 14.0,
        "event_type": "code",
        "phash": "2b3c4d5e6f708192",
        "ocr_text": "QueueProvider",
        "frame_uri": "local://frames/video-1/0004.png",
    },
    {
        "at_sec": 19.0,
        "event_type": "speaker",
        "phash": "3c4d5e6f708192a3",
        "ocr_text": "",
        "frame_uri": "local://frames/video-1/0005.png",
    },
    {
        "at_sec": 25.0,
        "event_type": "slide",
        "phash": "4d5e6f708192a3b4",
        "ocr_text": "Export ZIP",
        "frame_uri": "local://frames/video-1/0006.png",
    },
]

LLM_OUTPUTS: dict[str, dict[str, Any]] = {
    "refinement": {
        "boundaries": [
            {"start_sec": 0.0, "end_sec": 14.0, "title": "Introduction"},
            {"start_sec": 14.0, "end_sec": 28.0, "title": "Progress and export"},
        ]
    },
    "summary": {
        "title": "Architecture overview",
        "summary": "The pipeline keeps the browser separate from the worker: "
        "worker -> db -> sse -> browser.",
    },
    "style": {
        "style_profile": {
            "density": {"value": "balanced", "source": "examples"},
            "tone": {"value": "practical", "source": "examples"},
            "structure": {"value": "sections-with-screenshots", "source": "depth"},
        }
    },
}


class InMemoryQueue:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    def send(self, message: dict[str, object]) -> str:
        self.messages.append(message)
        return f"fake-message-{message.get('job_id', len(self.messages))}"

    def receive(self) -> dict[str, object] | None:
        return self.messages[0] if self.messages else None

    def complete(self, message: dict[str, object]) -> None:
        self.messages.remove(message)

    def dead_letter(self, message: dict[str, object], reason: str) -> dict[str, object]:
        return {"message": message, "reason": reason}


class LocalBlobStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> str:
        self.objects[key] = data
        return self.url_for(key)

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def url_for(self, key: str) -> str:
        return f"local://{key}"

    def delete_prefix(self, prefix: str) -> int:
        matching = [key for key in self.objects if key.startswith(prefix)]
        for key in matching:
            del self.objects[key]
        return len(matching)


class FakeResolver:
    def can_handle(self, url: str) -> bool:
        return url.startswith(("https://www.youtube.com/", "https://youtube.com/"))

    def resolve(self, url: str) -> dict[str, object]:
        return {"source_url": url, "canonical_url": "https://www.youtube.com/watch?v=fake"}


class FakeAcquirer:
    def download_proxy(self, video_id: str) -> str:
        return f"local://proxy/{video_id}.mp4"


class FakeTranscriptProvider:
    def fetch(self, video_id: str) -> list[dict[str, object]]:
        return [dict(span, video_id=video_id) for span in TRANSCRIPT_SAMPLE]


class FakeFrameSampler:
    def sample(self, video_id: str) -> list[dict[str, object]]:
        return [dict(event, video_id=video_id) for event in VISUAL_EVENTS_SAMPLE]


class FakeOcr:
    def extract_text(self, frame_id: str) -> str:
        if frame_id == "frame-1":
            return "Architecture overview"
        return ""


class FakeChatModel:
    def complete_json(self, prompt: str, schema: dict[str, object] | None = None) -> dict[str, Any]:
        del schema
        for kind, payload in LLM_OUTPUTS.items():
            if f"kind: {kind}" in prompt:
                return payload
        msg = "fake prompt must include kind: refinement, kind: summary, or kind: style"
        raise ValueError(msg)


class FakeEmbeddingModel:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = sha256(text.encode("utf-8")).digest()
        return [round(digest[index] / 255.0, 6) for index in range(8)]


@dataclass(frozen=True)
class FakeProfile:
    queue: InMemoryQueue
    blob_store: LocalBlobStore
    source_resolver: FakeResolver
    media_acquirer: FakeAcquirer
    transcript_provider: FakeTranscriptProvider
    frame_sampler: FakeFrameSampler
    ocr_provider: FakeOcr
    chat_model: FakeChatModel
    embedding_model: FakeEmbeddingModel

    def adapters(self) -> dict[str, object]:
        return {
            "queue": self.queue,
            "blob_store": self.blob_store,
            "source_resolver": self.source_resolver,
            "media_acquirer": self.media_acquirer,
            "transcript_provider": self.transcript_provider,
            "frame_sampler": self.frame_sampler,
            "ocr_provider": self.ocr_provider,
            "chat_model": self.chat_model,
            "embedding_model": self.embedding_model,
        }


def build_fake_profile() -> FakeProfile:
    return FakeProfile(
        queue=InMemoryQueue(),
        blob_store=LocalBlobStore(),
        source_resolver=FakeResolver(),
        media_acquirer=FakeAcquirer(),
        transcript_provider=FakeTranscriptProvider(),
        frame_sampler=FakeFrameSampler(),
        ocr_provider=FakeOcr(),
        chat_model=FakeChatModel(),
        embedding_model=FakeEmbeddingModel(),
    )
