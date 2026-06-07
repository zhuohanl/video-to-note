# Video-to-Note v2

## Overview

Video-to-Note v2 is a single-user Azure-first web app that turns a public conference or lecture video into structured notes. It resolves and proxies the media, builds transcript and visual evidence, segments the talk into clips, drafts a Markdown note, lets the user edit clips and review the note, then exports a ZIP containing `note.md`, screenshots, and metadata.

The authoritative product/design source is [docs/specs/2026-06-05-video-to-note-v2-design.md](docs/specs/2026-06-05-video-to-note-v2-design.md). The implementation checklist is [docs/plans/implementation_plan.md](docs/plans/implementation_plan.md).

## Architecture

The app has three deployable surfaces:

- `apps/web`: Next.js browser UI for login, submit, edit, review, and export.
- `apps/api`: FastAPI backend for auth, jobs, clips, notes, versions, exports, and SSE.
- `worker`: Python worker that consumes queued jobs and runs the media/transcript/visual/segment/draft/assemble pipeline.

The browser talks to the web/API surface only; it never calls the worker. The API creates jobs and enqueues work through the `QueueProvider` boundary. The worker writes durable state to PostgreSQL and artifacts to Blob storage. Progress flows worker -> `job_events` table and Postgres notifications -> API SSE -> browser timeline lanes.

Cloud deployments use Azure Container Apps for web/API and an Azure Container Apps Job for the worker, Azure Service Bus for the queue, Azure PostgreSQL for metadata, Azure Blob Storage for artifacts, Key Vault for secrets, Managed Identity for service-to-service auth, and Application Insights for telemetry.

## Run Locally

Local development uses the `fake` profile for zero-spend offline AI/media behavior. Store local config in your shell or `.env` using [.env.example](.env.example) as the key list; cloud secrets stay in Key Vault.

Start local dependencies:

```bash
docker compose up -d
```

Install Python and web dependencies:

```bash
uv sync --group dev
pnpm install
```

Apply database migrations:

```bash
uv run alembic upgrade head
```

Start the API:

```bash
uv run uvicorn vtn_api.main:app --reload --host 127.0.0.1 --port 8000
```

Run one worker drain loop when jobs are queued:

```bash
uv run python -m vtn_worker.main
```

Start the web app:

```bash
pnpm --dir apps/web dev
```

Open the web app at `http://127.0.0.1:3000/login`.

## Deploy

Deployment is intentionally two operator-facing commands: `azd up` provisions and deploys; `azd down --purge --force` tears the environment down.

Configure the azd environment as described in [docs/deploy.md](docs/deploy.md), then deploy:

```bash
azd up
```

Tear down:

```bash
azd down --purge --force
```

`azd up` runs Bicep provisioning, deploys the web/API/worker images, seeds Key Vault secrets, and applies Alembic migrations through the lifecycle hooks under `infra/hooks/`.

## Test

Default local tests exclude paid real-infra cases:

```bash
uv run ruff check .
uv run mypy packages apps/api worker
uv run pytest -m "not real_infra" --cov=packages --cov=apps --cov=worker --cov-fail-under=85 -q
pnpm --dir apps/web lint
pnpm --dir apps/web test
pnpm --dir apps/web e2e
pnpm --dir apps/web build
```

Focused acceptance commands:

```bash
uv run pytest tests/docs/test_readme.py -q
uv run python eval/segmentation/run.py
```

Real-infra tests are opt-in because they use live Azure resources:

```bash
uv run pytest -m real_infra
```

## Repo Map

| Path | Purpose |
| --- | --- |
| `apps/web` | Next.js frontend and Playwright journeys. |
| `apps/api` | FastAPI backend, auth, SSE, and HTTP routes. |
| `worker` | Queue consumer and pipeline orchestration. |
| `packages/vtn_core` | Shared domain models and settings. |
| `packages/vtn_ingest` | Source resolving and media acquisition helpers. |
| `packages/vtn_transcript` | Caption and ASR provider boundaries. |
| `packages/vtn_visual` | Frame sampling, OCR, and visual event extraction. |
| `packages/vtn_style` | Example-note style extraction and defaults. |
| `packages/vtn_segment` | Boundary detectors and fusion scoring. |
| `packages/vtn_notes` | Scene choice, summary, and note assembly. |
| `packages/vtn_export` | ZIP export projection. |
| `packages/vtn_storage` | PostgreSQL repositories, Blob storage, and queue providers. |
| `packages/vtn_ai` | Fake and Azure AI adapter seams. |
| `infra` | Bicep modules, azd hooks, and Azure resource declarations. |
| `migrations` | Alembic database migrations. |
| `tests` | Unit, contract, integration, e2e, docs, and opt-in real-infra tests. |
| `eval` | Segmentation evaluation harness and labeled fixtures. |
