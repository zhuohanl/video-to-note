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
VTN_USERNAME="${VTN_USERNAME:-local}"

if [[ -z "$KEY_VAULT_NAME" && -n "$RESOURCE_GROUP_NAME" ]]; then
  KEY_VAULT_NAME="$(az keyvault list --resource-group "$RESOURCE_GROUP_NAME" --query "[?tags.app=='video-to-note-v2'].name | [0]" -o tsv)"
fi

if [[ -z "$KEY_VAULT_NAME" ]]; then
  echo "KEY_VAULT_NAME is required. Run after azd provision or set it in the azd env." >&2
  exit 1
fi

if [[ -z "${VTN_PASSWORD_HASH:-}" ]]; then
  if [[ -z "${VTN_PASSWORD:-}" ]]; then
    echo "Set VTN_PASSWORD_HASH or VTN_PASSWORD in the azd env before azd up." >&2
    exit 1
  fi
  VTN_PASSWORD_HASH="$(VTN_PASSWORD="$VTN_PASSWORD" uv run python - <<'PY'
import bcrypt
import os

print(bcrypt.hashpw(os.environ["VTN_PASSWORD"].encode(), bcrypt.gensalt(rounds=12)).decode())
PY
)"
fi

if [[ -z "${VTN_COOKIE_SECRET:-}" ]]; then
  VTN_COOKIE_SECRET="$(uv run python - <<'PY'
import secrets

print(secrets.token_urlsafe(48))
PY
)"
  azd env set VTN_COOKIE_SECRET "$VTN_COOKIE_SECRET" >/dev/null
fi

az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name vtn-username --value "$VTN_USERNAME" --only-show-errors 1>/dev/null
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name vtn-password-hash --value "$VTN_PASSWORD_HASH" --only-show-errors 1>/dev/null
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name vtn-cookie-secret --value "$VTN_COOKIE_SECRET" --only-show-errors 1>/dev/null

echo "Seeded Video-to-Note login and cookie secrets in Key Vault '$KEY_VAULT_NAME'."
