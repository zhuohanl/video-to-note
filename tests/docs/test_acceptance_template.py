from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
TEMPLATE = ROOT / "docs" / "acceptance.template.md"


def test_acceptance_template_records_required_p6_final_evidence() -> None:
    assert TEMPLATE.exists()
    text = TEMPLATE.read_text()
    assert "Status: pending" in text
    assert "RUN_REAL=1 bash tests/infra/test_lifecycle.sh" in text
    assert "azd up" in text
    assert "uv run pytest -m real_infra" in text
    assert "azd down --purge --force" in text
    assert "Independent reviewer" in text
