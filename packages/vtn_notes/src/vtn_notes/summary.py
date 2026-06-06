from __future__ import annotations


class FakeSummaryGenerator:
    def summarize(self, *, title: str, summary_seed: str, outline: str) -> str:
        return f"{title}: {summary_seed}. Outline: {outline}"
