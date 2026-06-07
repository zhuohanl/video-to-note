from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
LIFECYCLE = ROOT / "tests" / "infra" / "test_lifecycle.sh"


def test_lifecycle_runs_full_real_pytest_suite_before_browser_journey() -> None:
    text = LIFECYCLE.read_text()
    full_suite = "RUN_REAL=1 uv run pytest -m real_infra"
    browser = "DEPLOYED_WEB_URL=\"$WEB_URL\" RUN_REAL=1 pnpm --dir apps/web exec playwright test"

    assert full_suite in text
    assert "-k deployed_journey" not in text
    assert text.index(full_suite) < text.index(browser)
    assert '"$AZD_BIN" down --purge --force' in text
