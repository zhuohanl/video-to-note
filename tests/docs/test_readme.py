from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
README = ROOT / "README.md"
ENV_EXAMPLE = ROOT / ".env.example"
REQUIRED_HEADINGS = [
    "## Overview",
    "## Architecture",
    "## Run Locally",
    "## Deploy",
    "## Test",
    "## Repo Map",
]
KNOWN_PREFIXES = ("uv ", "pnpm ", "docker compose ", "azd ")


def test_readme_has_required_sections_and_deploy_commands() -> None:
    assert README.exists()
    text = README.read_text()
    for heading in REQUIRED_HEADINGS:
        assert heading in text
    assert "azd up" in text
    assert "azd down" in text
    assert "TODO" not in text


def test_readme_command_blocks_use_known_prefixes() -> None:
    text = README.read_text()
    blocks = re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)
    assert blocks
    for block in blocks:
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            assert line.startswith(KNOWN_PREFIXES), line


def test_env_example_requests_plaintext_password_not_hash() -> None:
    text = ENV_EXAMPLE.read_text()
    assert "VTN_PASSWORD=" in text
    assert "VTN_PASSWORD_HASH=" not in text
