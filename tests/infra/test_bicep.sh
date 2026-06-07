#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

az bicep build --file infra/main.bicep

if [[ "${RUN_AZD_PREVIEW:-0}" == "1" ]]; then
  AZD_BIN="${AZD_BIN:-$(command -v azd || command -v azd.exe || command -v azd.cmd || true)}"
  if [[ -z "$AZD_BIN" ]] && command -v powershell.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
    AZD_WIN="$(powershell.exe -NoProfile -Command "(Get-Command azd -ErrorAction Stop).Source" | tr -d '\r')"
    AZD_BIN="$(cygpath -u "$AZD_WIN")"
  fi
  if [[ -z "$AZD_BIN" ]]; then
    echo "azd is required when RUN_AZD_PREVIEW=1." >&2
    exit 127
  fi
  "$AZD_BIN" provision --preview --no-prompt
else
  echo "Skipping azd provision --preview; set RUN_AZD_PREVIEW=1 when Azure credentials and azd env are available."
fi
