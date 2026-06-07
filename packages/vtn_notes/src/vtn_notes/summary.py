from __future__ import annotations

from typing import Any


class FakeSummaryGenerator:
    def summarize(self, *, title: str, summary_seed: str, outline: str) -> str:
        return f"{title}: {summary_seed}. Outline: {outline}"


def regenerate_summary(clip: dict[str, Any]) -> str:
    return FakeSummaryGenerator().summarize(
        title=str(clip["title"]),
        summary_seed=str(clip["summary_seed"]),
        outline=str(clip["title"]),
    )
