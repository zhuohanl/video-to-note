from __future__ import annotations

from copy import deepcopy
from typing import Any

from vtn_core.models import PromptDepth

DEPTH_DEFAULTS = {
    PromptDepth.brief: ("coarse", "low"),
    PromptDepth.balanced: ("medium", "medium"),
    PromptDepth.thorough: ("fine", "high"),
    PromptDepth.custom: ("medium", "medium"),
}


def resolve_style_profile(
    depth: PromptDepth,
    *,
    extracted: dict[str, Any] | None,
    custom_prompt: str | None,
    confidence_threshold: float = 0.75,
) -> dict[str, Any]:
    granularity_default, density_default = DEPTH_DEFAULTS[depth]
    extracted = deepcopy(extracted) if extracted else {}
    profile = {
        "style_descriptor": extracted.get("style_descriptor") or f"depth preset: {depth.value}",
        "granularity": _dimension(
            extracted.get("granularity"),
            fallback=granularity_default,
            threshold=confidence_threshold,
        ),
        "density": _dimension(
            extracted.get("density"),
            fallback=density_default,
            threshold=confidence_threshold,
        ),
        "derived_prompt": _derived_prompt(
            str(extracted.get("derived_prompt") or ""),
            custom_prompt,
        ),
        "extracted_from": extracted.get("extracted_from") or [],
    }
    return profile


def _dimension(value: object, *, fallback: str, threshold: float) -> dict[str, object]:
    if isinstance(value, dict):
        confidence = float(value.get("confidence") or 0.0)
        candidate = value.get("value")
        if isinstance(candidate, str) and confidence >= threshold:
            return {"value": candidate, "confidence": confidence, "source": "examples"}
    return {"value": fallback, "confidence": 1.0, "source": "depth"}


def _derived_prompt(extracted_prompt: str, custom_prompt: str | None) -> str:
    parts = [part for part in (extracted_prompt.strip(), (custom_prompt or "").strip()) if part]
    return "\n\n".join(parts)
