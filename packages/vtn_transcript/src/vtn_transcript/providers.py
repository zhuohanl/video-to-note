from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from vtn_core.models import TranscriptSource

from vtn_transcript.chain import TranscriptResult, TranscriptSpanData


class ProviderFailure(Exception):
    pass


class TranscriptProvider(Protocol):
    source: TranscriptSource

    def fetch(self, video_id: UUID) -> TranscriptResult: ...


@dataclass(frozen=True)
class StaticTranscriptProvider:
    source: TranscriptSource
    result: list[TranscriptSpanData] | ProviderFailure

    def fetch(self, video_id: UUID) -> TranscriptResult:
        del video_id
        if isinstance(self.result, ProviderFailure):
            raise self.result
        return TranscriptResult(source=self.source, spans=self.result)


class TranscriptProviderChain:
    def __init__(self, providers: list[TranscriptProvider]) -> None:
        self.providers = providers

    def fetch(self, video_id: UUID) -> TranscriptResult:
        failures: list[ProviderFailure] = []
        for provider in self.providers:
            try:
                result = provider.fetch(video_id)
            except ProviderFailure as exc:
                failures.append(exc)
                continue
            if result.source == TranscriptSource.azure_speech and failures:
                return TranscriptResult(
                    source=result.source,
                    spans=result.spans,
                    warning=("asr_fallback", "Using Azure Speech fallback"),
                )
            return result
        raise ProviderFailure("all transcript providers failed")


@dataclass(frozen=True)
class AzureSpeechProvider:
    key: str
    region: str
    audio_path: str
    language: str = "en-US"

    def fetch_real(self) -> TranscriptResult:
        query = urllib.parse.urlencode({"language": self.language})
        url = (
            f"https://{self.region}.stt.speech.microsoft.com/speech/recognition/"
            f"conversation/cognitiveservices/v1?{query}"
        )
        with open(self.audio_path, "rb") as audio:
            request = urllib.request.Request(
                url,
                data=audio.read(),
                headers={
                    "Ocp-Apim-Subscription-Key": self.key,
                    "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                    "Accept": "application/json",
                },
                method="POST",
            )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = str(payload.get("DisplayText") or "").strip()
        if not text:
            raise ProviderFailure("Azure Speech returned no transcript text")
        return TranscriptResult(
            source=TranscriptSource.azure_speech,
            spans=[TranscriptSpanData(Decimal("0.000"), Decimal("0.000"), text, None)],
        )
