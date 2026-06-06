from __future__ import annotations

from vtn_core.models import PromptDepth
from vtn_style.extract import StyleChatModel, extract_style_from_examples
from vtn_style.resolve import resolve_style_profile

from vtn_worker.runner import StageContext


async def extract_style(
    context: StageContext,
    *,
    chat_model: StyleChatModel | None = None,
) -> None:
    prompt = context.repo.get_prompt(context.job_id)
    depth = PromptDepth(prompt["depth"])
    examples = list(prompt["examples"] or [])
    custom_prompt = prompt["custom_prompt"]
    extracted = None
    if examples and chat_model is not None:
        try:
            extracted = extract_style_from_examples(examples, chat_model=chat_model)
        except Exception as exc:
            context.repo.emit_event(
                context.job_id,
                "warning",
                {"code": "style_fallback", "message": str(exc)},
            )

    profile = resolve_style_profile(depth, extracted=extracted, custom_prompt=custom_prompt)
    context.repo.set_style_profile(context.job_id, profile)
    if extracted is not None and prompt["save_style_as_default"]:
        context.repo.upsert_style_default(examples, extracted)
    context.repo.emit_event(context.job_id, "style.resolved", {"profile": profile})
