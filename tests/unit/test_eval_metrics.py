from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from vtn_core.settings import SegmentationSettings

ROOT = Path(__file__).parents[2]
HARNESS_PATH = ROOT / "eval" / "segmentation" / "run.py"


def _load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("segmentation_eval_run", HARNESS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


harness = _load_harness()


def test_boundary_metric_counts_one_to_one_matches() -> None:
    result = harness.score_boundaries(
        [10.0, 20.0, 40.0],
        [9.0, 21.0, 30.0],
        tolerance_sec=2.0,
    )

    assert result.true_positives == 2
    assert result.false_positives == 1
    assert result.false_negatives == 1
    assert round(result.precision, 3) == 0.667
    assert round(result.recall, 3) == 0.667


def test_eval_harness_runs_tiny_fixture() -> None:
    report = harness.run(
        Path("eval/segmentation/labels"),
        SegmentationSettings(
            merge_window_sec=4.0,
            min_score=0.5,
        ),
    )

    assert report["labels"][0]["id"] == "tiny_talk"
    assert report["summary"]["precision"] >= 0.75
    assert report["summary"]["recall"] >= 0.75
