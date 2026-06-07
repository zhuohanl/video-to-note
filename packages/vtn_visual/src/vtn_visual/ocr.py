from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field


class OcrFailure(Exception):
    pass


@dataclass(frozen=True)
class FakeOcrProvider:
    text_by_name: Mapping[str, str]
    fail_for: set[str] = field(default_factory=set)

    def extract_text(self, frame_path: str) -> str:
        name = frame_path.replace("\\", "/").rsplit("/", 1)[-1]
        if name in self.fail_for:
            raise OcrFailure(f"OCR failed for {name}")
        return self.text_by_name.get(name, "")


@dataclass(frozen=True)
class AzureVisionOcrProvider:
    endpoint: str
    key: str

    def extract_text(self, frame_path: str) -> str:
        url = self.endpoint.rstrip("/") + "/computervision/imageanalysis:analyze"
        query = urllib.parse.urlencode({"features": "read", "api-version": "2024-02-01"})
        with open(frame_path, "rb") as frame:
            request = urllib.request.Request(
                f"{url}?{query}",
                data=frame.read(),
                headers={
                    "Ocp-Apim-Subscription-Key": self.key,
                    "Content-Type": "application/octet-stream",
                    "Accept": "application/json",
                },
                method="POST",
            )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        lines: list[str] = []
        read_result = payload.get("readResult")
        if isinstance(read_result, dict):
            for block in read_result.get("blocks", []):
                if not isinstance(block, dict):
                    continue
                for line in block.get("lines", []):
                    if isinstance(line, dict) and line.get("text"):
                        lines.append(str(line["text"]))
        return "\n".join(lines)
