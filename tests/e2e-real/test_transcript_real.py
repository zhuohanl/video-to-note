from __future__ import annotations

import os

import pytest
from vtn_transcript.providers import AzureSpeechProvider
from vtn_visual.ocr import AzureVisionOcrProvider


@pytest.mark.real_infra
def test_azure_speech_transcribes_real_audio() -> None:
    required = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "VTN_SPIKE_AUDIO_PATH")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        pytest.skip(f"missing Azure Speech env vars: {', '.join(missing)}")

    result = AzureSpeechProvider(
        key=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
        audio_path=os.environ["VTN_SPIKE_AUDIO_PATH"],
    ).fetch_real()

    assert result.spans
    assert all(span.text for span in result.spans)


@pytest.mark.real_infra
def test_azure_vision_ocr_reads_real_slide() -> None:
    required = ("AZURE_VISION_ENDPOINT", "AZURE_VISION_KEY", "VTN_SPIKE_FRAME_PATH")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        pytest.skip(f"missing Azure Vision env vars: {', '.join(missing)}")

    text = AzureVisionOcrProvider(
        endpoint=os.environ["AZURE_VISION_ENDPOINT"],
        key=os.environ["AZURE_VISION_KEY"],
    ).extract_text(os.environ["VTN_SPIKE_FRAME_PATH"])

    assert text.strip()
