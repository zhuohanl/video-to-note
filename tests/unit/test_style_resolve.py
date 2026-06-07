from __future__ import annotations

from vtn_core.invariants import assert_style_profile_valid
from vtn_core.models import PromptDepth
from vtn_style.resolve import resolve_style_profile


def test_style_resolve_depth_only_profile_when_no_examples() -> None:
    profile = resolve_style_profile(PromptDepth.brief, extracted=None, custom_prompt=None)

    assert profile["granularity"] == {"value": "coarse", "confidence": 1.0, "source": "depth"}
    assert profile["density"] == {"value": "low", "confidence": 1.0, "source": "depth"}
    assert profile["style_descriptor"] == "depth preset: brief"
    assert_style_profile_valid(profile)


def test_style_resolve_confident_example_wins() -> None:
    profile = resolve_style_profile(
        PromptDepth.balanced,
        extracted={
            "style_descriptor": "Use compact bullets",
            "granularity": {"value": "fine", "confidence": 0.91},
            "density": {"value": "high", "confidence": 0.87},
            "derived_prompt": "Prefer bullet lists",
            "extracted_from": [{"name": "example.md", "blob_path": "examples/job/example.md"}],
        },
        custom_prompt=None,
    )

    assert profile["granularity"] == {"value": "fine", "confidence": 0.91, "source": "examples"}
    assert profile["density"] == {"value": "high", "confidence": 0.87, "source": "examples"}
    assert profile["derived_prompt"] == "Prefer bullet lists"
    assert_style_profile_valid(profile)


def test_style_resolve_thin_example_falls_back_to_depth_and_merges_custom_prompt() -> None:
    profile = resolve_style_profile(
        PromptDepth.thorough,
        extracted={
            "style_descriptor": "Thin sample",
            "granularity": {"value": "coarse", "confidence": 0.2},
            "density": {"value": "low", "confidence": 0.1},
            "derived_prompt": "Use terse notes",
            "extracted_from": [],
        },
        custom_prompt="Include code snippets",
    )

    assert profile["granularity"] == {"value": "fine", "confidence": 1.0, "source": "depth"}
    assert profile["density"] == {"value": "high", "confidence": 1.0, "source": "depth"}
    assert profile["derived_prompt"] == "Use terse notes\n\nInclude code snippets"
    assert_style_profile_valid(profile)
