#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

load_azd_env() {
  if command -v azd >/dev/null 2>&1; then
    eval "$(azd env get-values)"
  elif command -v azd.exe >/dev/null 2>&1; then
    eval "$(azd.exe env get-values)"
  elif command -v powershell.exe >/dev/null 2>&1; then
    AZD_WIN="$(powershell.exe -NoProfile -Command "(Get-Command azd -ErrorAction Stop).Source" | tr -d '\r')"
    if command -v cygpath >/dev/null 2>&1; then
      eval "$("$(cygpath -u "$AZD_WIN")" env get-values)"
    fi
  fi
}

load_azd_env

KEY_VAULT_NAME="${KEY_VAULT_NAME:-${AZURE_KEY_VAULT_NAME:-}}"
RESOURCE_GROUP_NAME="${RESOURCE_GROUP_NAME:-${AZURE_RESOURCE_GROUP:-${AZURE_RESOURCE_GROUP_NAME:-}}}"
POSTGRES_SERVER_NAME="${POSTGRES_SERVER_NAME:-${AZURE_POSTGRES_SERVER_NAME:-}}"

if [[ -z "$KEY_VAULT_NAME" && -n "$RESOURCE_GROUP_NAME" ]]; then
  KEY_VAULT_NAME="$(az keyvault list --resource-group "$RESOURCE_GROUP_NAME" --query "[?tags.app=='video-to-note-v2'].name | [0]" -o tsv)"
fi

if [[ -z "$POSTGRES_SERVER_NAME" && -n "$RESOURCE_GROUP_NAME" ]]; then
  POSTGRES_SERVER_NAME="$(az postgres flexible-server list --resource-group "$RESOURCE_GROUP_NAME" --query "[?tags.app=='video-to-note-v2'].name | [0]" -o tsv)"
fi

if [[ -z "$KEY_VAULT_NAME" || -z "$POSTGRES_SERVER_NAME" || -z "$RESOURCE_GROUP_NAME" ]]; then
  echo "KEY_VAULT_NAME, POSTGRES_SERVER_NAME, and RESOURCE_GROUP_NAME are required for migration." >&2
  exit 1
fi

PUBLIC_IP="$(uv run python - <<'PY'
from urllib.request import urlopen

print(urlopen("https://api.ipify.org", timeout=10).read().decode())
PY
)"

az postgres flexible-server firewall-rule create \
  --resource-group "$RESOURCE_GROUP_NAME" \
  --name "$POSTGRES_SERVER_NAME" \
  --rule-name azd-migration-client \
  --start-ip-address "$PUBLIC_IP" \
  --end-ip-address "$PUBLIC_IP" \
  --only-show-errors 1>/dev/null

export DATABASE_URL
DATABASE_URL="$(az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name database-url --query value -o tsv)"

uv run alembic upgrade head

echo "Applied Alembic migrations to '$POSTGRES_SERVER_NAME'."
