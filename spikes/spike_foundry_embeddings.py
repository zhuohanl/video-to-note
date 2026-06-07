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
        "AZURE_OPENAI_EMBED_DEPLOYMENT",
    )
    client = AzureOpenAI(
        azure_endpoint=env["AZURE_OPENAI_ENDPOINT"],
        api_key=env["AZURE_OPENAI_API_KEY"],
        api_version="2025-04-01-preview",
    )
    response = client.embeddings.create(
        model=env["AZURE_OPENAI_EMBED_DEPLOYMENT"],
        input=["alpha", "beta", "gamma"],
    )
    print(
        json.dumps(
            {"dimensions": len(response.data[0].embedding), "count": len(response.data)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
