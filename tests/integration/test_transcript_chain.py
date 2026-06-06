from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from vtn_core.models import TranscriptSource
from vtn_transcript.chain import TranscriptSpanData
from vtn_transcript.providers import (
    ProviderFailure,
    StaticTranscriptProvider,
    TranscriptProviderChain,
)


def test_transcript_chain_uses_best_available_provider() -> None:
    video_id = uuid4()
    source = StaticTranscriptProvider(
        TranscriptSource.source_captions,
        [
            TranscriptSpanData(Decimal("0.000"), Decimal("1.500"), "Official captions", None),
        ],
    )
    youtube = StaticTranscriptProvider(
        TranscriptSource.youtube_captions,
        [
            TranscriptSpanData(Decimal("0.000"), Decimal("1.500"), "YouTube captions", None),
        ],
    )

    result = TranscriptProviderChain([source, youtube]).fetch(video_id)

    assert result.source == TranscriptSource.source_captions
    assert result.spans[0].text == "Official captions"
    assert result.warning is None


def test_transcript_chain_falls_back_to_asr_with_warning() -> None:
    video_id = uuid4()
    source = StaticTranscriptProvider(
        TranscriptSource.source_captions,
        ProviderFailure("no source"),
    )
    youtube = StaticTranscriptProvider(
        TranscriptSource.youtube_captions,
        ProviderFailure("no youtube captions"),
    )
    asr = StaticTranscriptProvider(
        TranscriptSource.azure_speech,
        [
            TranscriptSpanData(Decimal("0.000"), Decimal("1.500"), "ASR text", None),
        ],
    )

    result = TranscriptProviderChain([source, youtube, asr]).fetch(video_id)

    assert result.source == TranscriptSource.azure_speech
    assert result.spans[0].text == "ASR text"
    assert result.warning == ("asr_fallback", "Using Azure Speech fallback")
