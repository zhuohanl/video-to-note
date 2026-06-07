from __future__ import annotations

import asyncio

from vtn_core.cost import estimate
from vtn_core.models import PromptDepth
from vtn_ingest.resolve import FakeResolver, ResolveError, ResolverRegistry

from vtn_worker.runner import PipelineError, StageContext


async def resolve_job(
    context: StageContext,
    registry: ResolverRegistry | None = None,
) -> None:
    resolver_registry = registry or ResolverRegistry([FakeResolver()])
    source_url = context.repo.get_job_source_url(context.job_id)
    try:
        resolved = resolver_registry.resolve(source_url)
    except ResolveError as exc:
        raise PipelineError(exc.code, exc.message, context.stage) from exc

    await asyncio.to_thread(
        context.repo.claim_canonical_video,
        job_id=context.job_id,
        canonical_url=resolved.canonical_url,
        source_type=resolved.source_type,
        title=resolved.title,
        duration_sec=resolved.duration_sec,
    )
    depth = PromptDepth(context.repo.get_prompt(context.job_id)["depth"])
    refined = estimate(resolved.duration_sec, depth)
    context.repo.update_cost_estimate(context.job_id, refined)
    context.repo.emit_event(context.job_id, "cost.estimate", refined)
