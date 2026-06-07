from __future__ import annotations

import json

from common import require_env, require_real
from openai import AzureOpenAI


def main() -> int:
    if not require_real():
        return 0
    env = require_env(
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT",
    )
    client = AzureOpenAI(
        azure_endpoint=env["AZURE_OPENAI_ENDPOINT"],
        api_key=env["AZURE_OPENAI_API_KEY"],
        api_version="2025-04-01-preview",
    )
    response = client.chat.completions.create(
        model=env["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        messages=[{"role": "user", "content": "Return JSON: {\"ok\": true}"}],
        response_format={"type": "json_object"},
    )
    print(json.dumps({"content": response.choices[0].message.content}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
