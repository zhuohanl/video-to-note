from __future__ import annotations

from typing import Any, Protocol


class StyleChatModel(Protocol):
    def complete_json(
        self,
        prompt: str,
        schema: dict[str, object] | None = None,
    ) -> dict[str, Any]: ...


def extract_style_from_examples(
    examples: list[dict[str, Any]],
    *,
    chat_model: StyleChatModel,
) -> dict[str, Any]:
    prompt = "\n\n".join(str(example.get("markdown") or "") for example in examples)
    payload = chat_model.complete_json(
        f"kind: style\nExtract style dimensions from examples:\n{prompt}",
        schema={"type": "object"},
    )
    return validate_extracted_style(payload, examples)


def validate_extracted_style(
    payload: dict[str, Any],
    examples: list[dict[str, Any]],
) -> dict[str, Any]:
    for key in ("style_descriptor", "granularity", "density", "derived_prompt"):
        if key not in payload:
            raise ValueError(f"style extraction missing {key}")
    for key in ("granularity", "density"):
        dimension = payload[key]
        if (
            not isinstance(dimension, dict)
            or "value" not in dimension
            or "confidence" not in dimension
        ):
            raise ValueError(f"style extraction invalid {key}")
    extracted = dict(payload)
    extracted["extracted_from"] = [
        {
            "name": str(example.get("name") or "example.md"),
            "blob_path": str(
                example.get("blob_path") or f"examples/{example.get('name', 'example.md')}"
            ),
        }
        for example in examples
    ]
    return extracted
