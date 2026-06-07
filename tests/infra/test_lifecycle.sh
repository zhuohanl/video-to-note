#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ "${RUN_REAL:-0}" != "1" ]]; then
  echo "Skipping real Azure lifecycle test. Set RUN_REAL=1 to run azd up/down against a throwaway environment."
  exit 0
fi

AZD_BIN="${AZD_BIN:-$(command -v azd || command -v azd.exe || command -v azd.cmd || true)}"
if [[ -z "$AZD_BIN" ]] && command -v powershell.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
  AZD_WIN="$(powershell.exe -NoProfile -Command "(Get-Command azd -ErrorAction Stop).Source" | tr -d '\r')"
  AZD_BIN="$(cygpath -u "$AZD_WIN")"
fi

if [[ -z "$AZD_BIN" ]]; then
  echo "azd is required for the real lifecycle test." >&2
  exit 127
fi

uv run python tests/infra/preflight_real_infra.py --phase pre-up

cleanup() {
  "$AZD_BIN" down --purge --force || true
}
trap cleanup EXIT

"$AZD_BIN" up --no-prompt

eval "$("$AZD_BIN" env get-values)"

eval "$(uv run python tests/infra/preflight_real_infra.py --phase post-up --format shell)"

API_URL="${API_URL:-${AZURE_API_URL:-}}"
KEY_VAULT_NAME="${KEY_VAULT_NAME:-${AZURE_KEY_VAULT_NAME:-}}"
RESOURCE_GROUP_NAME="${RESOURCE_GROUP_NAME:-${AZURE_RESOURCE_GROUP:-${AZURE_RESOURCE_GROUP_NAME:-}}}"
VTN_USERNAME="${VTN_USERNAME:-local}"

if [[ -z "$KEY_VAULT_NAME" && -n "$RESOURCE_GROUP_NAME" ]]; then
  KEY_VAULT_NAME="$(az keyvault list --resource-group "$RESOURCE_GROUP_NAME" --query "[?tags.app=='video-to-note-v2'].name | [0]" -o tsv)"
fi

if [[ -z "$API_URL" || -z "${VTN_PASSWORD:-}" || -z "$RESOURCE_GROUP_NAME" || -z "$KEY_VAULT_NAME" ]]; then
  echo "API_URL, VTN_PASSWORD, KEY_VAULT_NAME, and RESOURCE_GROUP_NAME/AZURE_RESOURCE_GROUP are required after azd up." >&2
  exit 1
fi

DATABASE_URL="${DATABASE_URL:-$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name database-url --query value -o tsv)}"
VTN_PASSWORD_HASH="${VTN_PASSWORD_HASH:-$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name vtn-password-hash --query value -o tsv)}"
VTN_COOKIE_SECRET="${VTN_COOKIE_SECRET:-$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name vtn-cookie-secret --query value -o tsv)}"
export DATABASE_URL VTN_PASSWORD_HASH VTN_COOKIE_SECRET

uv run python tests/infra/preflight_real_infra.py --phase final

curl --fail --silent "$API_URL/healthz" >/dev/null
curl --fail --silent \
  --request POST \
  --header "content-type: application/json" \
  --data "{\"username\":\"$VTN_USERNAME\",\"password\":\"$VTN_PASSWORD\"}" \
  "$API_URL/login" >/dev/null

DEPLOYED_API_URL="$API_URL" RUN_REAL=1 uv run pytest -m real_infra

WEB_URL="${WEB_URL:-${AZURE_WEB_URL:-}}"

if [[ -z "$WEB_URL" ]]; then
  echo "WEB_URL is required after azd up for deployed browser e2e." >&2
  exit 1
fi

DEPLOYED_WEB_URL="$WEB_URL" RUN_REAL=1 pnpm --dir apps/web exec playwright test e2e/journey.deployed.spec.ts

"$AZD_BIN" down --purge --force
trap - EXIT

if az group show --name "$RESOURCE_GROUP_NAME" --only-show-errors >/dev/null 2>&1; then
  echo "Resource group '$RESOURCE_GROUP_NAME' still exists after azd down." >&2
  exit 1
fi

echo "Real Azure lifecycle test passed and resource group '$RESOURCE_GROUP_NAME' was removed."
