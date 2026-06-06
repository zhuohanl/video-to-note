# Video-to-Note v2 — Implementation Plan

> Produced by `planning-from-spec`. **Plan only — do not start code until reviewed.**
> Execute in a fresh session that reads only this plan + the spec.

## Source of truth (priority order)

On conflict the order is **design (spec) > this plan > spike observations**. The design document is
authoritative for all product behaviour and contracts; the plan must conform, never the reverse.
Spikes are empirical inputs that may refine *implementation details the design leaves open* (exact
API flags, SDK quirks, observed limits) — they do **not** override the design. If a spike's findings
**contradict** required design behaviour or a contract, that is a **blocker**: stop, record it in
the spike writeup, and raise an explicit design-review decision before implementing. Do not silently
edit the spec to match the spike.

1. **Spec / design** — `docs/specs/2026-06-05-video-to-note-v2-design.md` (authoritative for all
   product behaviour and contracts; the north star).
2. **This plan** — task decomposition only; conforms to the spec.
3. **Empirical spikes** — `spikes/*.md` (external API behaviour). Refine implementation details
   where the spec is silent; any contradiction with the spec is a blocked design decision, not an
   override.
4. Secondary (informative, never overriding): `frontend-design/high-fidelity/v2/*` (UI reference),
   `docs/prompt/raw.md`.

Spec section references below are by heading, e.g. *(spec: Data model)*.

---

## Goal

Turn a public YouTube / Microsoft-conference session URL into a reviewed Markdown note with
de-duplicated screenshots, via an Azure-first pipeline (resolve → acquire → analyze → segment →
draft → assemble) that streams progress to a timeline Edit page and a document Review page, with
durable version history and ZIP export.

## Architecture

Monorepo: a Next.js frontend, a FastAPI **API**, and a Python **worker** (ACA Job) decoupled by a
`QueueProvider` (Azure Service Bus in cloud, in-memory locally). Shared Python packages
(`vtn_*`) own one pipeline concern each; the worker orchestrates them and packages never import the
worker. State lives in PostgreSQL (jobs/clips/notes/versions/events) + Blob (proxy/frames/exports/
examples). Progress flows worker → `job_events` table + `LISTEN/NOTIFY` → API SSE → browser; the
browser never calls the worker. AI/media access sits behind Protocol-seam adapters with a `fake`
profile for offline, deterministic tests.

## Tech stack

- **Backend/worker:** Python 3.12, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0 (async, asyncpg),
  Alembic, `pytest` + `pytest-asyncio` + `httpx`. Tooling: `uv` workspace, `ruff`, `mypy`.
- **Media/AI:** `yt-dlp`, `ffmpeg` (subprocess), `Pillow` + `imagehash` (pHash), `scikit-image`
  (SSIM), `openai` (Azure OpenAI via Foundry), `azure-cognitiveservices-speech`,
  `azure-ai-documentintelligence` / Vision (OCR), `azure-servicebus`, `azure-storage-blob`,
  `azure-identity` (`DefaultAzureCredential`).
- **Frontend:** Next.js 15 (App Router), React 19, TypeScript, `pnpm`, Vitest + Testing Library,
  Playwright (e2e). Markdown editor via TipTap/ProseMirror or a textarea+preview (decided in F24).
- **Infra/CI:** Bicep + `azd`, GitHub Actions, `docker-compose` (Postgres + Azurite).

---

## Prerequisites — check before you start

Verify every box below **before P0**. Group A is needed for all local work; Group B only when you
run the opt-in real-infra tests or deploy (P3 real adapters, P6, P6-FINAL). Each box has a
verification command — tick it only after the command succeeds.

### A. Local toolchain & services (needed from P0 onward)
- [ ] **Python 3.12** — `python --version` shows 3.12.x. *(Note: the dev machine currently has 3.11;
  install 3.12 or let `uv` manage it via `uv python install 3.12`.)*
- [ ] **uv** installed — `uv --version` succeeds.
- [ ] **Node 20+** and **pnpm** — `node --version` ≥ 20, `pnpm --version` succeeds.
- [ ] **Docker Desktop running** — `docker info` exits 0 (daemon up), and `docker compose version`
  succeeds. *(Local Postgres + Azurite run here.)*
- [ ] **ffmpeg on PATH** — `ffmpeg -version` succeeds. *(Not present on the dev machine yet — install
  it; needed for visual sampling + frame-on-demand.)*
- [ ] **git** — `git --version` succeeds; repo cloned and on a working branch.
- [ ] **Local stack up** — `docker compose up -d` then a `SELECT 1` against Postgres and a container
  list against Azurite both succeed (becomes true once P0-T2 lands; re-check before integration runs).

### B. Cloud access & credentials (needed for `-m real_infra` tests + deploy: P3, P6, P6-FINAL)
- [ ] **Azure CLI** — `az version` succeeds; **`az login`** completed into the **target tenant**, and
  `az account show` points at the **intended subscription** (use a throwaway subscription/RG for the
  P6-FINAL acceptance run).
- [ ] **Azure Developer CLI** — `azd version` succeeds; **`azd auth login`** completed.
- [ ] **Subscription roles** — the signed-in identity has the RBAC roles listed in
  `spikes/azure_auth.md` (from P0-S0) — at minimum contributor on the target RG plus data-plane roles
  for Storage/Key Vault/Service Bus/AI. Verify with the P0-S0 spike: `RUN_REAL=1 uv run python
  spikes/spike_azure_auth.py` exits 0.
- [ ] **AI capacity in region** — Azure AI Foundry chat + embedding deployments, Azure AI Speech, and
  Vision/Document Intelligence exist (or quota is available) in the target region.
- [ ] **Local secrets for dev** — `.env` populated from `.env.example` (credential hash + cookie
  signing secret + any model ids/endpoints); in cloud these come from Key Vault via Managed Identity,
  never committed.
- [ ] **P0-S0 credentials spike green** — **hard gate:** no `[TEST-E2E-REAL]` / deploy task runs until
  `spikes/azure_auth.md` records a successful auth + cheap round-trip.

> If a Group A box can't be ticked, fix it before P0. If a Group B box can't be ticked, you can still
> do all default-on work (P0–P5 mocked tiers) but **not** the real-infra tests or deploy; flag it as
> blocked rather than skipping silently.

---

## Contracts (every task references this; do not redefine per-task)

> **Single source of truth.** The spec already owns the data, API, event, and reconciliation
> contracts. This section **points at the spec** and records only the deltas the spec leaves open
> (wire types, error-envelope shape, DI seams). Tasks reference these; they never invent their own.

### C1 — Data contract

The PostgreSQL schema is **spec: Data model (PostgreSQL)** — `videos`, `jobs`, `prompts`,
`style_defaults`, `transcript_spans`, `visual_events`, `clips`, `notes`, `note_versions`,
`job_events`, `exports`, `job_costs`, plus the unique indexes (`uq_videos_canonical`,
`uq_spans_video_start`, `uq_visual_video_at_type`, `UNIQUE(job_id, order_index)`,
`UNIQUE(job_id, seq)`). Migration `0001_initial` materializes it verbatim (Task P1-T2).
`prompts.style_profile` JSON shape is **spec: Data model** (the `style_profile` JSON block).

Python domain models (`vtn_core/models.py`, Pydantic v2) mirror these tables 1:1 with enums:
`JobStage = queued|resolving|acquiring_media|analyzing|segmenting|drafting`;
`JobStatus = active|review_ready|exported|failed|canceled`;
`ArtifactState = absent|building|ready`;
`ClipStatus = pending|ready`; `Classification = text_led|visual_led|mixed`;
`SceneSource = auto|manual`; `VersionKind = initial|auto_edit|auto_pre_change|auto_rebuild|manual|restore`;
`TranscriptSource = source_captions|youtube_captions|azure_speech`;
`SourceType = youtube|msbuild|msignite|other`.

### C2 — API contract

The endpoint list, methods, payloads, status codes, and the three ETag scopes are **spec: API
contract**. The plan adds only the wire envelope:

- **Error envelope** (every non-2xx): `{"error": {"code": string, "message": string}}`.
- **Error codes:** `unsupported_url`, `video_unavailable`, `transcript_failed`,
  `job_not_review_ready` (409), `needs_ack` (409), `stale_write` (412), `version_not_found` (404),
  `unauthorized` (401), `validation_error` (422).
- **ETag scopes** (spec: API contract): single-clip ETag = `clips.updated_at`; clips-collection
  ETag = `max(clips.updated_at)` over the job; note ETag = `notes.updated_at`. Sent as `If-Match`;
  restore + manual version-save require **both** note ETag and clips-collection ETag (comma-sep).
- **Auth:** all non-`/login` routes require the signed `httpOnly` `vtn_session` cookie; SSE too.

### C3 — Event contract (SSE)

Event `type`s, when emitted, payloads, and frontend reactions are **spec: Event contract (SSE)**:
`stage`, `cost.estimate`, `style.resolved`, `clip.ready`, `warning`, `error`, `done`. Each
`job_events` row → one SSE event; `id` = `job_events.id` (bigserial), used for `Last-Event-ID`
replay. The parallel `analyzing` fork emits per-branch `stage` events (`transcribe`/`index visual`/
`extract style`) while `jobs.stage` stays `analyzing` (spec: The parallel `analyzing` fork).

### C4 — Internal seams (Protocol/DI — production never imports test fakes)

All defined in their owning package as `typing.Protocol`; real adapters and the `fake` profile both
implement them; the worker/API receive them by injection. A `Profile` selector
(`vtn_ai.profile.get_profile(name)`, name ∈ `{azure, fake}`) returns the wired set.

| Protocol | Package | Real impl | Fake impl |
|---|---|---|---|
| `QueueProvider` (`send`, `receive`, `complete`, `dead_letter`) | `vtn_storage` | `ServiceBusQueue` | `InMemoryQueue` / SQLite |
| `BlobStore` (`put`, `get`, `url_for`, `delete_prefix`) | `vtn_storage` | `AzureBlobStore` | `LocalBlobStore` (Azurite or tmp) |
| `SourceResolver` (`can_handle`, `resolve`) | `vtn_ingest` | YouTube/MSEvent/Generic | `FakeResolver` |
| `MediaAcquirer` (`download_proxy`) | `vtn_ingest` | `YtDlpAcquirer` | `FakeAcquirer` |
| `TranscriptProvider` (`fetch`) | `vtn_transcript` | SourceCaptions/YouTube/AzureSpeech | `FakeTranscriptProvider` |
| `FrameSampler` / `OcrProvider` | `vtn_visual` | ffmpeg / Azure Vision | `FakeFrameSampler` / `FakeOcr` |
| `ChatModel` (`complete_json`) | `vtn_ai` | `FoundryChatModel` | `FakeChatModel` |
| `EmbeddingModel` (`embed`) | `vtn_ai` | `FoundryEmbeddingModel` | `FakeEmbeddingModel` |

**Rule:** the production packages must not import from `tests/` or `fixtures/`. Fakes live in
`vtn_ai`/`vtn_storage`/etc. under a `fake` submodule and are selected by profile, injected through
the same Protocol the real adapter uses.

### C5 — Shared invariant module (`vtn_core/invariants.py`)

ONE reusable assertion module, called from every test layer **and** on the output of every real run
(worker stage exit + export). It encodes the spec's hard rules:

- `assert_note_no_transcript(markdown)` — `notes.markdown` never contains a transcript blockquote
  marker (spec: Initial note assembly — "Transcript blocks are never persisted").
- `assert_note_no_regen_marker(markdown)` — stored markdown never contains "⚠ Needs regeneration"
  (spec: Assembled Markdown while `needs_regen=true`).
- `assert_clips_contiguous_ordered(clips)` — `order_index` is 0..n-1 dense, time ranges
  non-overlapping and ascending (spec: clips / split-merge renumber).
- `assert_unique_order_index(clips)` — `UNIQUE(job_id, order_index)` holds.
- `assert_baseline_immutable(versions)` — exactly one `seq=1`, `is_baseline=true`, `kind=initial`.
- `assert_export_structure(zip)` — `note.md` + `images/NNNN-*.png` (one per clip) + `metadata.json`
  present; image paths in `note.md` are relative and resolve (spec: Export format).
- `assert_style_profile_valid(profile)` — required keys + per-dimension `source∈{examples,depth}`.
- `assert_reconciliation_flags(note, op)` — flag transitions match spec: Reconciliation (encoded in
  Task F17-T1).
- `assert_note_content_flags(note)` — `include_summary OR include_transcript` (the at-least-one rule;
  spec: Content selection is a render-time projection). The DB `CHECK (include_summary OR
  include_transcript)` is the backstop; this asserts it at every materialized-note boundary.

---

## Feature list

Coverage: every spec capability maps to exactly one feature row; boundaries are disjoint.

| ID | Feature | In scope (boundary) | NOT in scope (neighbor owns) | Phase | Depends on |
|----|---------|---------------------|------------------------------|-------|------------|
| F0  | Auth & session | `POST /login`, cookie sign/verify, route guard, SSE cookie auth | everything else | P2 | Contracts |
| F1  | Submit & job creation | `POST /jobs`, placeholder video, enqueue, `GET /jobs/{id}`, cost estimate at submit | resolving (F2), cost actuals (F20) | P2 | F0, QueueProvider |
| F2  | Resolving stage | `SourceResolver` registry, validate public, canonical claim + re-submit dedup | artifact CAS (F3), download (F4) | P2/P3 | C4 |
| F3  | Shared video artifact concurrency | per-artifact CAS claim/wait/recover on `videos.*_state` | the artifacts themselves (F4/F5/F6) | P3 | F2 |
| F4  | Media acquisition | yt-dlp proxy @720p → Blob, skip-if-present | serving the proxy (F12) | P2/P3 | F3 |
| F5  | Transcript acquisition | provider chain → `transcript_spans`, source recorded, ASR-fallback warning | visual (F6) | P2/P3 | F4 |
| F6  | Visual indexing | two-tier ffmpeg sampling, detectors, OCR, pHash → `visual_events`+frames | scene pick (F9) | P2/P3 | F4 |
| F7  | Style extraction & resolution | LLM extract + deterministic depth-merge → `style_profile`, `style.resolved` | usage in F8/F9 | P3 | F5/F6, F1 |
| F8  | Segmentation | `BoundaryDetector`s, fusion, snap, LLM refinement → `clips` (pending) | drafting (F9) | P2/P3 | F5, F6, F7 |
| F9  | Drafting | scene selection (pHash dedup) + per-clip summary, `clip.ready` | assembly (F10) | P2/P3 | F8 |
| F10 | Initial note assembly | step-9 assembler, `notes` row, baseline `seq=1` version, `done` | editing (F13+) | P2 | F9 |
| F11 | SSE progress transport | `job_events` writes, `LISTEN/NOTIFY`, SSE endpoint, `Last-Event-ID` replay | per-event producers (each stage) | P2 | F0, C3 |
| F12 | Media serving | proxy range stream, scene-candidates, frame-on-demand `POST /clips/{id}/scene` | clip flag logic (F13) | P4 | F4, F6 |
| F13 | Clip content edits | `PATCH /clips/{id}` (title/summary/caption), single-clip ETag, auto-sync, needs_ack | split/merge (F14), regen (F15) | P4 | F10 |
| F14 | Clip structural edits | `split`/`merge`, collection ETag, renumber, deterministic placeholder values | content edits (F13) | P4 | F13 |
| F15 | Clip regenerate | `POST /clips/{id}/regenerate`, single-clip ETag, needs_ack/auto-sync | edits (F13/F14) | P4 | F13, F9 |
| F16 | Note editing | `GET/PUT/PATCH /note`, autosave coalesce, content-selection flags `include_summary`/`include_transcript` (booleans only, at-least-one) | rebuild/keep (F17) | P4 | F10 |
| F17 | Reconciliation | rebuild/keep, `is_polished`/`clips_dirty` state machine, modals' source flags | versions (F18) | P4 | F13, F16 |
| F18 | Versioning | save/list/restore, full-project snapshots, both-ETag guard, non-destructive | reconciliation triggers (F17) | P4 | F10, F17 |
| F19 | Export | ZIP assembly, render-time projections (regen marker, transcript), `metadata.json` | note storage (F10) | P4 | F10, F12 |
| F20 | Cost model | estimate at submit + record actuals, `cost.estimate` event | banner UI (F22) | P3 | F1 |
| F21 | FE: Login | login form → cookie → route gating | other routes | P5 | F0 |
| F22 | FE: Submit | URL+depth+examples+cost banner → `POST /jobs` → navigate | edit page (F23) | P5 | F1, F20 |
| F23 | FE: Edit page | timeline 4 lanes, SSE consumer, progressive fill, gated tools, split/merge/set-scene/regen | review (F24) | P5 | F11, F12, F13, F14, F15 |
| F24 | FE: Review page | doc editor, caption edit, content selector (Summary/Transcript/Both), version history, rebuild/keep banner | export (F25) | P5 | F16, F17, F18 |
| F25 | FE: Export page | summary card, ZIP contents, download | — | P5 | F19 |
| F26 | Infra (IaC) | Bicep + `azure.yaml`, Key Vault, MI, App Insights, all Azure resources; **one-command `azd up` provision+deploy / `azd down` teardown**; deployed-env `[TEST-E2E-REAL]` (API journey F26-T3 + browser journey F26-T4) between up and down | app code | P6 | P2–P5 green |
| F27 | CI/CD | GitHub Actions lint/type/test/build + deploy + `alembic upgrade head` | infra (F26) | P6 | F26 |
| F28 | Segmentation eval harness | labeled-talk recall/precision scoring vs config weights | fusion code (F8) | P6 | F8 |
| F29 | README & top-level docs | `README.md`: what the app does, architecture, run-locally, deploy (`azd up`/`down`), test, repo map | per-package internals | P6 | F26 (deploy steps), P2–P5 (run steps) |
| F-SB | Azure Service Bus QueueProvider (real) | `ServiceBusQueue` impl of the `QueueProvider` Protocol + DLQ + duplicate-safe receive | Protocol/in-memory impl (P1-T5) | P6 | P1-T5, [SPIKE] S8 |

**Not features (cross-cutting groundwork, early phases):** monorepo scaffold, domain models, full
migration, contracts-as-code, fake profile, fixtures, invariant module, all spikes.

---

## Phases

| Phase | Contains | Gate (command that passes) |
|-------|----------|----------------------------|
| **P0 Foundation** | scaffold, deps, docker-compose, fake profile, fixtures, all SPIKEs | every `spikes/*` script exits 0 (real-infra spikes opt-in); `uv run pytest -q` + `pnpm test` smoke exit 0 |
| **P1 Contracts** | domain models, migration `0001`, API/SSE/queue/storage/AI Protocols, invariant module | `uv run pytest tests/contracts -q` exits 0; `alembic upgrade head && alembic downgrade base` clean |
| **P2 MVP pipeline (fake)** | F0, F1, F11, F2/F4/F5/F6/F8/F9 (fake adapters), F10 | mocked e2e `submit→review_ready→GET note` green; invariants pass on output |
| **P3 Real media + AI** | real F2/F4/F5/F6/F8/F9 adapters, F7, F20 | integration (Postgres+Azurite+fake AI) green; real-infra e2e (opt-in) green on tiny video |
| **P4 Editing backend** | F12, F13, F14, F15, F16, F17, F18, F19 | per-feature acceptance + mocked e2e of full edit/review/export round-trip green |
| **P5 Frontend** | F21–F25 | Playwright mocked e2e of login→submit→edit→review→export green; component tests green |
| **P6 Infra/CI/eval/real queue/docs** | F26, F27, F28, F29, F-SB | CI green on PR; eval harness emits recall/precision report; `README.md` present and accurate; **P6-FINAL acceptance green — `azd up` → full `-m real_infra` suite (incl. deployed API + browser journeys) → `azd down --purge` — with `docs/acceptance.md` recorded** |

No feature depends on a later phase. Each phase ends with an **independent-reviewer gate** (a second
agent/model reads spec + diff + claimed acceptance + the invariants the gate owns) run **after** the
test gates — resolution: BLOCKING → fix & re-run; MEDIUM → fix now if small else tracked follow-up;
LOW/clean → proceed.

---

## Implementation checklist (task tracker)

One box per task — tick it only when **all the task's internal `- [ ]` steps are green and its
Acceptance command passes**. This is the at-a-glance "what's done / what's left". Phase-gate boxes
roll up the phase. (Each task block further down also carries its own granular step checkboxes.)

### P0 — Foundation
- [x] P0-T1 — uv workspace + 10 packages + api/worker scaffold
- [x] P0-T2 — docker-compose (Postgres + Azurite) + Next.js scaffold
- [x] P0-T3 — fixtures + `fake` profile skeleton
- [ ] P0-S0 — SPIKE: Azure credentials / liveness (gates all real-infra)
- [x] P0-S1 — SPIKE: yt-dlp
- [x] P0-S2 — SPIKE: ffmpeg
- [x] P0-S3 — SPIKE: pHash
- [ ] P0-S4 — SPIKE: Azure Speech ASR
- [ ] P0-S5 — SPIKE: Azure Vision / Document Intelligence OCR
- [ ] P0-S6 — SPIKE: Azure OpenAI chat (Foundry)
- [ ] P0-S7 — SPIKE: Azure OpenAI embeddings
- [ ] P0-S8 — SPIKE: Azure Service Bus
- [x] P0-S9 — SPIKE: Postgres LISTEN/NOTIFY + advisory lock
- [ ] **P0 phase gate** — spikes green; smoke tests green; reviewer pass

### P1 — Contracts as code
- [x] P1-T1 — domain models + enums + state machine
- [x] P1-T2 — Alembic migration 0001 (full schema, up+down verified)
- [x] P1-T3 — API request/response schemas + error envelope
- [x] P1-T4 — SSE event models
- [x] P1-T5 — storage Protocols + InMemory/Local impls + repos
- [x] P1-T6 — invariant module (C5)
- [x] **P1 phase gate** — `tests/contracts` green; migration up+down clean; reviewer pass

### P2 — MVP pipeline (fake)
- [x] F0-T1 — cookie sign/verify + `POST /login`
- [x] F1-T1 — `POST /jobs` + `GET /jobs/{id}`
- [x] F11-T1 — event writer + SSE endpoint + replay
- [x] P2-W1 — worker consumer + stage runner skeleton
- [x] F2-T1 (fake) — resolving + canonical claim + dedup
- [x] F4/F5/F6-T1 (fake) — media + transcript + visual stages
- [x] F8-T1 (fake) — segmenting (signals + fusion + refinement)
- [x] F9-T1 (fake) — drafting (scene selection + clip summary)
- [x] F10-T1 — initial note assembly + baseline version
- [x] P2-A1 — read endpoints (`GET /clips`, `GET /note`)
- [x] P2-E1 — `[TEST-E2E-MOCK]` submit → review_ready → GET note
- [x] **P2 phase gate** — mocked e2e green; invariants pass; coverage; reviewer pass

### P3 — Real media + AI + style + cost
- [x] F3-T1 — per-artifact CAS claim/wait/recover
- [x] F2/F4-T2 (real) — resolvers + yt-dlp acquirer
- [ ] F5/F6-T2 (real) — transcript chain + ffmpeg/OCR/pHash
- [ ] F8/F9-T2 (real) — Foundry chat + embeddings
- [x] F7-T1 — style extraction + resolution
- [x] F20-T1 — cost estimate + actuals
- [ ] P3-E1 — `[TEST-E2E-REAL]` tiny real video → review_ready (opt-in)
- [ ] **P3 phase gate** — integration green; real-infra e2e green; reviewer pass

### P4 — Editing & reconciliation backend
- [x] F12-T1 — media serving + frame-on-demand
- [x] F13-T1 — `PATCH /clips/{id}` + auto-sync / needs_ack
- [x] F14-T1 — split / merge + placeholder values
- [x] F15-T1 — regenerate
- [x] F16-T1 — note autosave + content-selection flags
- [x] F17-T1 — rebuild / keep + flag state machine
- [x] F18-T1 — versioning (save / restore)
- [x] F19-T1 — export ZIP + projections
- [x] P4-E2 — `[TEST-E2E-MOCK]` full edit→review→export round-trip
- [ ] **P4 phase gate** — mocked e2e (P2-E1+P4-E2) green; coverage; reviewer pass

### P5 — Frontend
- [ ] F21-T1 — login + route gating
- [ ] F22-T1 — submit form + depth + examples + cost banner
- [ ] F23-T1 — edit SSE consumer + progressive lanes + gated tools
- [ ] F23-T2 — split/merge/set-scene/regenerate + inspector + modal
- [ ] F24-T1 — review doc editor + caption + content selector + versions + rebuild banner
- [ ] F25-T1 — export page
- [ ] P5-E1 — `[TEST-E2E]` Playwright journey (mocked backend)
- [ ] **P5 phase gate** — component tests + Playwright green; coverage; reviewer pass

### P6 — Infra, CI/CD, eval, real queue, docs
- [ ] F26-T1 — Bicep modules + `azure.yaml` for `azd up`/`down`
- [ ] F26-T2 — one-command lifecycle (`azd up` working env / `azd down` teardown)
- [ ] F26-T3 — `[TEST-E2E-REAL]` deployed API journey (opt-in)
- [ ] F26-T4 — `[TEST-E2E-REAL]` deployed browser journey (opt-in)
- [ ] F27-T1 — GitHub Actions CI + CD (migrate/deploy)
- [ ] F-SB-T1 — `ServiceBusQueue` + DLQ + duplicate-safe receive
- [ ] F28-T1 — segmentation eval harness
- [ ] P6-E1 — `[TEST-E2E-REAL]` full real-infra e2e incl. real Service Bus (opt-in)
- [ ] F29-T1 — `README.md` + top-level docs
- [ ] P6-FINAL — `[TEST-E2E-REAL]` mandatory end-of-build real-infra acceptance run
- [ ] **P6 final gate** — CI green; P6-FINAL green (`azd up`→full real suite→`azd down`); `docs/acceptance.md` recorded; reviewer pass

---

## Test layers (schedule each; drop none)

| Layer | Proves | Default | When | Command |
|---|---|---|---|---|
| Unit | pure fns: resolvers, normalization, detectors, fusion scoring, scene scoring, assembler, flag transitions, placeholder derivation | on | per pure fn | `uv run pytest tests/unit -q` |
| Integration (fakes) | stages/endpoints wired against **real Postgres + Azurite + in-memory queue + fake AI**; STRICT gate for error/timeout/retry/fallback branches | on | per stage/endpoint | `uv run pytest tests/integration -q` |
| Mocked/smoke e2e `[TEST-E2E-MOCK]` | full app (API+worker) flow with AI faked via DI; owns deterministic branch coverage | on | from thinnest slice onward | `uv run pytest tests/e2e -q` |
| Real-infra e2e `[TEST-E2E-REAL]` | live wiring vs **real Azure AI + real Service Bus + real Blob** on a tiny real video; schema/happy-path/audit. Flavors: worker-run-locally vs real services (P3-E1, P6-E1); **deployed API journey (F26-T3)**; **deployed browser journey (F26-T4)**. All run together once at **P6-FINAL** (`azd up`→suite→`azd down`) | **OFF** (`-m real_infra`) | from first slice touching real infra; grows per feature; mandatory end-of-build run at P6-FINAL | `uv run pytest -m real_infra` |
| FE component | timeline split/merge/set-scene, doc editor, rebuild/keep, version flows, SSE replay | on | per FE feature | `pnpm test` |
| FE e2e (Playwright, mocked backend) | login→submit→edit→review→export | on | P5 | `pnpm e2e` |

### Ownership (one owner per guarantee)

| Guarantee | Owning tier |
|---|---|
| Schema validity, unique indexes, advisory-lock CAS, `UNIQUE(job_id,order_index)` renumber under contention | integration (real Postgres) |
| ASR fallback / refinement fallback / OCR failure → warning (not hard fail) | mocked e2e (STRICT — must fire via DI) |
| ETag `412` and `409 needs_ack`/`job_not_review_ready` branches | mocked e2e (STRICT) |
| LISTEN/NOTIFY + `Last-Event-ID` replay | integration (real Postgres) |
| Real Foundry/Speech/Vision/embeddings/Service Bus shape, auth, serialization | real-infra e2e (opt-in) |
| Full user journey + persistence | mocked e2e (deterministic) + real-infra e2e (confidence) |
| Reconciliation flag state machine + worked example v1→v4 | integration + unit |
| Note never stores transcript/regen-marker; export structure | invariant module, called by all tiers |

**Measurable completion gate:** `pytest --cov=packages --cov=apps --cov=worker
--cov-fail-under=85` wired into CI as an acceptance command; FE `pnpm test --coverage` threshold 80%.

---

## P0 — Foundation

### File map (created this phase)

- `pyproject.toml` (uv workspace root), `uv.lock`
- `packages/vtn_*/pyproject.toml` + `src/<pkg>/__init__.py` (10 packages per spec: Repository structure)
- `apps/api/pyproject.toml`, `apps/api/vtn_api/main.py`
- `worker/pyproject.toml`, `worker/vtn_worker/main.py`
- `apps/web/` (Next.js scaffold via `create-next-app`), `apps/web/package.json`, `pnpm-workspace.yaml`
- `docker-compose.yml` (Postgres 16 + Azurite), `.env.example`
- `fixtures/` (canned transcript/visual/LLM JSON + a tiny sample `.md` example note)
- `spikes/` (one trio per external dep)
- `ruff.toml`, `mypy.ini`, `pytest.ini`, `.github/workflows/ci.yml` (skeleton, lint+test only)
- `tests/{unit,integration,e2e,contracts}/conftest.py`

### Task [SETUP] P0-T1: uv workspace + 10 packages + api + worker scaffold

**Files:** `pyproject.toml`, `packages/*/pyproject.toml`, `packages/*/src/<pkg>/__init__.py`,
`apps/api/...`, `worker/...`, `ruff.toml`, `mypy.ini`, `pytest.ini`.

- [x] Create root `pyproject.toml` declaring a `uv` workspace with members `packages/*`, `apps/api`,
  `worker`. Each member depends on the `vtn_*` it needs (per spec: Repository structure dependency
  rules — `vtn_style` is depended on by `vtn_segment`+`vtn_notes`; packages never import the worker).
- [x] Each package exposes a `hello()` returning its name (placeholder to prove import wiring).
- [x] Write `tests/unit/test_imports.py` importing all 10 packages + asserting `vtn_segment` can
  import `vtn_style` but `vtn_style` cannot import `vtn_segment` (circular-import guard).
- [x] Run `uv sync && uv run pytest tests/unit/test_imports.py -q` → expect PASS.
- [x] `git commit -m "P0: uv workspace + package scaffold"`

**Acceptance:** `uv run pytest tests/unit/test_imports.py -q` exits 0; `uv run ruff check .` and
`uv run mypy packages apps worker` exit 0. *(spec: Repository structure)*

### Task [SETUP] P0-T2: docker-compose (Postgres + Azurite) + Next.js scaffold

**Files:** `docker-compose.yml`, `.env.example`, `apps/web/*`, `pnpm-workspace.yaml`.

- [x] `docker-compose.yml`: `postgres:16` (db `vtn`, exposes 5432) and `azurite` (blob port 10000).
- [x] `create-next-app` into `apps/web` (TS, App Router); add Vitest + Testing Library + Playwright.
- [x] Write `apps/web/__tests__/smoke.test.tsx` rendering a trivial component; `tests/integration/
  test_db_up.py` connecting to Postgres and `SELECT 1`.
- [x] Run `docker compose up -d`, then `uv run pytest tests/integration/test_db_up.py -q` and
  `pnpm -C apps/web test` → expect PASS.
- [x] `git commit -m "P0: docker-compose + Next.js scaffold"`

**Acceptance:** `docker compose up -d` healthy; `SELECT 1` integration test exits 0; `pnpm test`
smoke exits 0. *(spec: Local dev; Deployment and CI/CD)*

### Task [SETUP] P0-T3: fixtures + `fake` profile skeleton

**Files:** `fixtures/transcript_sample.json`, `fixtures/visual_events_sample.json`,
`fixtures/llm/{refinement,summary,style}.json`, `fixtures/examples/sample_note.md`,
`packages/vtn_ai/src/vtn_ai/fake/__init__.py`, `packages/vtn_ai/src/vtn_ai/profile.py`.

- [x] Author canned fixtures: a ~5-span transcript, ~6 visual events (mixed types, with phash +
  ocr_text), and deterministic LLM JSON outputs matching the schemas defined in P1.
- [x] `FakeChatModel.complete_json(prompt, schema)` returns the matching fixture by a `kind` tag;
  `FakeEmbeddingModel.embed(texts)` returns deterministic vectors (hash-seeded, no `random`).
- [x] `get_profile("fake")` returns the wired fake set (C4 table).
- [x] Test `tests/unit/test_fake_profile.py`: profile returns all 8 Protocols; fake chat returns
  schema-valid JSON for each `kind`.
- [x] Run → PASS. `git commit -m "P0: fixtures + fake profile"`

**Acceptance:** `uv run pytest tests/unit/test_fake_profile.py -q` exits 0; production packages
contain no import of `tests/` or `fixtures/` (grep check in the test). *(spec: Local dev — `fake` AI
profile; Decided defaults)*

### Spikes (P0) — one trio each: `spikes/sig_<dep>.py`, `spikes/spike_<dep>.py`, `spikes/<dep>.md`

Each spike writeup pins version + date + observed behaviour + **the contract it locks**. Trivial
stdlib needs none; everything with network/auth/3rd-party SDK does. The external-service rows in C4
are **derived from** these spikes.

### Task [SPIKE] P0-S0: Azure credentials / liveness (gates ALL real-infra tasks)

**Files:** `spikes/sig_azure_auth.py`, `spikes/spike_azure_auth.py`, `spikes/azure_auth.md`.

- [ ] Dump `DefaultAzureCredential` token acquisition; do a cheap authenticated round-trip to each
  resource group endpoint (Foundry models list, Storage container list, Service Bus namespace).
- [ ] Writeup records: which credential chain link succeeds locally vs in ACA (Managed Identity),
  required env vars, and the minimal RBAC roles.

**Acceptance:** `RUN_REAL=1 uv run python spikes/spike_azure_auth.py` exits 0 and prints a valid
token expiry; `azure_auth.md` lists the env/role contract. **No `[TEST-E2E-REAL]` task runs until
this is green.** *(spec: Security and configuration; Deployment)*

### Task [SPIKE] P0-S1..S9: external dependencies

One task each (same shape — sig dump, smallest live call, writeup locking the contract):

- **S1 yt-dlp** — resolve + download a 30s clip at 720p; record the format-selector string, output
  container, and failure modes (`video_unavailable`, age-gated). Locks `MediaAcquirer` contract.
- **S2 ffmpeg** — coarse 1fps sample + single-frame extract at a timestamp + scene-diff; record CLI
  flags, output naming, exit codes. Locks `FrameSampler` + frame-on-demand contract.
- **S3 pHash** (`imagehash`/`Pillow`) — phash two near-dup frames; record hash length + Hamming
  threshold that separates dup/non-dup. Locks dedup contract (F6/F9).
- **S4 Azure Speech ASR** — transcribe 20s audio from a proxy; record span shape, speaker labels
  availability, timeout. Locks `AzureSpeechProvider`.
- **S5 Azure Vision/Document Intelligence OCR** — OCR one slide frame; record text+bbox shape,
  rate/size limits, failure → warning. Locks `OcrProvider`.
- **S6 Azure OpenAI chat (Foundry)** — `complete_json` with a strict JSON schema; record the
  structured-output mechanism (response_format/tool), retry on invalid JSON, token/latency. Locks
  `ChatModel`.
- **S7 Azure OpenAI embeddings** — embed 3 strings; record dim + batch limit. Locks `EmbeddingModel`
  (used by `SemanticShiftDetector`).
- **S8 Azure Service Bus** — send/receive/complete/dead-letter one message with `job_id`+`attempt`;
  record duplicate-delivery + lock-renewal behaviour. Locks `QueueProvider`.
- **S9 Postgres LISTEN/NOTIFY + advisory lock** — `pg_advisory_xact_lock(hashtext(url))`, the
  `INSERT ... ON CONFLICT DO NOTHING` canonical claim, and `LISTEN`/`NOTIFY` round-trip with
  `asyncpg`. Locks the dedup-claim + SSE transport contracts (F2, F3, F11).

**Acceptance (each):** `RUN_REAL=1 uv run python spikes/spike_<dep>.py` exits 0 against the real
service (S2/S3 local) and `spikes/<dep>.md` records the exact response shape + failure behaviour the
C4 contract row is derived from. A spike may pin implementation details the spec leaves open (flags,
limits, SDK mechanics). **If a spike contradicts required spec behaviour or a contract, do NOT edit
the spec to match — stop, record the contradiction as a BLOCKER in the writeup, and raise an explicit
design-review decision before implementing** (per *Source of truth*). *(spec: Pipeline detailed
algorithms; Architecture)*

**Phase P0 gate:** all spike scripts exit 0 (real-infra ones under `RUN_REAL=1`, recorded as run);
smoke tests green; independent-reviewer pass on the spike writeups vs the C4 contract table.

---

## P1 — Contracts as code

### File map

- `packages/vtn_core/src/vtn_core/models.py` (Pydantic models + enums, C1)
- `packages/vtn_core/src/vtn_core/state_machine.py` (legal stage/status transitions)
- `packages/vtn_core/src/vtn_core/invariants.py` (C5)
- `packages/vtn_core/src/vtn_core/settings.py` (config: weights, thresholds, model_config, timeouts)
- `migrations/env.py`, `migrations/versions/0001_initial.py` (C1 schema verbatim)
- `apps/api/vtn_api/schemas.py` (request/response Pydantic, C2), `apps/api/vtn_api/errors.py` (envelope)
- `apps/api/vtn_api/events.py` (SSE event models, C3)
- `packages/vtn_storage/src/vtn_storage/{queue.py,blob.py,repos.py}` (Protocols + InMemory/Local)
- `tests/contracts/*`

### Task [CONTRACT] P1-T1: domain models + enums + state machine

**Files:** `vtn_core/models.py`, `vtn_core/state_machine.py`, `tests/contracts/test_models.py`.

- [x] Define every C1 model as a Pydantic v2 class with the spec's columns/types and the enums.
- [x] `state_machine.legal_transition(from_stage, to_stage)` and `legal_status(from, to)` encoding
  spec: Job state machine (e.g. `queued→resolving→...→drafting`; `active→review_ready→exported`;
  `active→failed`; no `exported→active`).
- [x] Test: round-trip each model to/from dict; assert illegal transitions raise (e.g.
  `drafting→resolving`, `exported→active`); assert enums match spec literals exactly.
- [x] Run → PASS. `git commit -m "P1: domain models + state machine"`

**Acceptance:** `uv run pytest tests/contracts/test_models.py -q` exits 0; mypy clean. *(spec: Domain
model and job lifecycle; Data model)*

### Task [CONTRACT] P1-T2: Alembic migration 0001 (full schema)

**Files:** `migrations/env.py`, `migrations/versions/0001_initial.py`,
`tests/contracts/test_migration.py`.

- [x] Translate spec: Data model SQL verbatim into the migration `upgrade()` (all 12 tables + every
  index + every unique index + CHECK constraints + `gen_random_uuid()` default — enable `pgcrypto`).
  `downgrade()` drops them in FK order.
- [x] Test (real Postgres): `alembic upgrade head`; introspect that every table/column/constraint
  from the spec exists (assert `uq_videos_canonical`, `uq_spans_video_start`,
  `uq_visual_video_at_type`, `UNIQUE(job_id,order_index)`, `UNIQUE(job_id,seq)`, the single-row CHECK
  on `style_defaults`); then `alembic downgrade base` leaves zero `vtn` tables.
- [x] Run → PASS. `git commit -m "P1: migration 0001 initial schema"`

**Acceptance:** `alembic upgrade head` then `alembic downgrade base` both exit 0; introspection test
finds all spec constraints. **Rollback verified.** *(spec: Data model; Migrations)*

### Task [CONTRACT] P1-T3: API request/response schemas + error envelope

**Files:** `apps/api/vtn_api/schemas.py`, `apps/api/vtn_api/errors.py`,
`tests/contracts/test_api_schemas.py`.

- [x] Pydantic models for every endpoint body in C2 (spec: API contract): `LoginBody`, `CreateJob`,
  `JobView`, `ClipView` (+ per-clip ETag), `ClipsView` (+ collection ETag), `NoteView`, `PatchClip`,
  `SplitBody`, `MergeBody`, `PutNote`, `PatchNote`, `VersionView`, `CreateVersion`, `ExportView`.
- [x] `errors.py`: `ApiError(code, message, http_status)` → JSON `{"error":{code,message}}`; a
  FastAPI exception handler; the C2 error-code constants.
- [x] Test: each schema validates a good payload and rejects a bad one with `validation_error`; the
  error handler renders the exact envelope for each code.
- [x] Run → PASS. `git commit -m "P1: API schemas + error envelope"`

**Acceptance:** `uv run pytest tests/contracts/test_api_schemas.py -q` exits 0; the envelope shape
matches C2 byte-for-byte. *(spec: API contract)*

### Task [CONTRACT] P1-T4: SSE event models (C3)

**Files:** `apps/api/vtn_api/events.py`, `tests/contracts/test_events.py`.

- [x] One model per event `type` with the spec payloads; `to_sse(row)` renders
  `id: {job_events.id}\nevent: {type}\ndata: {json}\n\n`.
- [x] Test: each event type serializes to a well-formed SSE frame with an `id:` line for replay.
- [x] Run → PASS. `git commit -m "P1: SSE event models"`

**Acceptance:** test exits 0; every C3 event type covered. *(spec: Event contract)*

### Task [CONTRACT] P1-T5: storage Protocols + InMemory/Local impls + repos

**Files:** `vtn_storage/queue.py`, `vtn_storage/blob.py`, `vtn_storage/repos.py`,
`tests/contracts/test_storage.py`.

- [x] `QueueProvider` + `InMemoryQueue` (and a SQLite-backed variant for the worker process);
  `BlobStore` + `LocalBlobStore` (Azurite via connection string, or tmp). Repos = thin SQLAlchemy
  data-access objects per aggregate (jobs, videos, clips, notes, versions, events, costs, exports).
- [x] Test (real Postgres + Azurite): enqueue→receive→complete; dead_letter path; blob put→get→
  url_for→delete_prefix; a repo insert/select round-trip for `jobs`.
- [x] Run → PASS. `git commit -m "P1: storage protocols + impls + repos"`

**Acceptance:** test exits 0 against Postgres+Azurite; `InMemoryQueue` and `ServiceBusQueue`
(stubbed until P6) share the `QueueProvider` Protocol. *(spec: Queue abstraction; Architecture)*

### Task [CONTRACT] P1-T6: invariant module (C5)

**Files:** `vtn_core/invariants.py`, `tests/contracts/test_invariants.py`.

- [x] Implement every assertion in C5 with precise checks (regex for transcript/regen markers,
  contiguity over sorted clips, baseline uniqueness, export structure via `zipfile`).
- [x] Test: each assertion passes on a valid fixture and raises a typed `InvariantError` with a
  clear message on a crafted violation (transcript leaked into markdown, duplicate order_index, two
  baselines, missing image, etc.).
- [x] Run → PASS. `git commit -m "P1: shared invariant module"`

**Acceptance:** `uv run pytest tests/contracts/test_invariants.py -q` exits 0; every invariant has a
positive and a negative test. *(spec: Initial note assembly; Export format; Versioning)*

**Phase P1 gate:** `uv run pytest tests/contracts -q` exits 0; migration up+down clean;
independent-reviewer pass (contracts vs spec data/API/event sections — hunt name/type drift).

---

## P2 — MVP pipeline (fake adapters), thinnest runnable slice + first e2e

Goal: a job submitted via the API runs end-to-end **on fake adapters** through every stage to
`review_ready`, streaming events, producing clips + an assembled note that satisfies the invariants.
This is the thinnest slice; the mocked e2e is written here and grows every later feature.

### File map

- `apps/api/vtn_api/auth.py`, `routes/jobs.py`, `sse.py`, `deps.py`, `main.py` (wire app)
- `worker/vtn_worker/main.py` (queue consumer + stage runner), `worker/vtn_worker/stages/*.py`
- `packages/vtn_ingest`, `vtn_transcript`, `vtn_visual`, `vtn_segment`, `vtn_notes` — fake-backed
  stage entrypoints (real adapters land in P3 behind the same Protocols)
- `tests/e2e/test_submit_to_review.py`

### [P2] Feature F0 — Auth & session

**Boundary:** login + cookie + guard only. **Contracts used:** C2 (auth, `unauthorized`).

#### Task [API] F0-T1: cookie sign/verify + `POST /login`

**Files:** `apps/api/vtn_api/auth.py`, `routes/login.py`, `tests/integration/test_auth.py`.

- [ ] `sign_session()`/`verify_session()` using an HMAC secret (from env locally, Key Vault in
  cloud); `POST /login` compares `password` against a bcrypt hash (env/Key Vault), sets `vtn_session`
  `httpOnly`,`Secure`,`SameSite=Lax` on success, else `401 unauthorized`.
- [ ] `require_session` dependency → `401 unauthorized` when cookie missing/invalid.
- [ ] Test: good creds → 200 + `Set-Cookie`; bad creds → 401 envelope; a guarded route → 401 without
  cookie, 200 with a signed cookie.
- [ ] Run → PASS. `git commit -m "F0: auth + login"`

**Acceptance:** `uv run pytest tests/integration/test_auth.py -q` exits 0; guarded route returns the
C2 `unauthorized` envelope without a valid cookie. *(spec: Security and configuration; Login)*

### [P2] Feature F1 — Submit & job creation

**Boundary:** create job + placeholder video + enqueue + read job + estimate. **Contracts:** C1,
C2 (`POST /jobs`, `GET /jobs/{id}`).

#### Task [API] F1-T1: `POST /jobs` creates job + placeholder video + enqueues

**Files:** `apps/api/vtn_api/routes/jobs.py`, `tests/integration/test_create_job.py`.

- [ ] Validate body (`url`, `depth∈{thorough,balanced,brief,custom}`, `custom_prompt?`, `examples?`,
  `use_saved_style?`); on `depth=custom` require `custom_prompt` (else `validation_error`).
- [ ] In one transaction: insert placeholder `videos` (canonical_url null, keyed on source_url),
  `jobs` (`stage=queued,status=active`), `prompts` row (depth/custom/examples/save flag), a
  `job_costs` estimate row (F20 computes the number; here store a deterministic estimate stub), then
  `QueueProvider.send({job_id, attempt:0})`. Return `202 {job_id, cost_estimate}`.
- [ ] `GET /jobs/{id}` → status, stage, flags, cost (or `404`).
- [ ] Test: POST → 202 with job_id + estimate; rows exist; queue has one message; `GET` returns
  `queued/active`; `depth=custom` without prompt → 422.
- [ ] Run → PASS. `git commit -m "F1: POST /jobs + GET /jobs/{id}"`

**Acceptance:** `uv run pytest tests/integration/test_create_job.py -q` exits 0; exactly one queue
message enqueued; placeholder video + job + prompts + cost rows present. *(spec: API contract —
Session & job creation; URL resolution — placeholder video)*

### [P2] Feature F11 — SSE progress transport

**Boundary:** `job_events` writes + `LISTEN/NOTIFY` + SSE endpoint + replay. **Contracts:** C3.

#### Task [API] F11-T1: event writer + `GET /jobs/{id}/events` SSE with replay

**Files:** `apps/api/vtn_api/sse.py`, `vtn_storage/repos.py` (`emit_event`),
`tests/integration/test_sse.py`.

- [ ] `emit_event(job_id, type, payload)` inserts a `job_events` row inside the caller's
  transaction and `NOTIFY vtn_job_<id>`. SSE endpoint: authenticate via cookie, replay rows with
  `id > Last-Event-ID`, then `LISTEN` and stream new rows as C3 frames; heartbeat comments.
- [ ] Test (real Postgres): emit 3 events; open SSE → receive 3; reconnect with `Last-Event-ID=2` →
  receive only event 3; unauthenticated → 401.
- [ ] Run → PASS. `git commit -m "F11: SSE transport + replay"`

**Acceptance:** test exits 0; replay returns exactly the events after `Last-Event-ID`; SSE requires
the cookie. *(spec: Progress event transport; Event contract)*

### [P2] Worker pipeline (fake adapters) — Features F2/F4/F5/F6/F8/F9 (fake), F10

> In P2 each stage runs against the **fake** profile through its Protocol seam. P3 swaps in real
> adapters behind the same seams. Each stage: skip-if-present, deterministic artifact key by
> `job_id`+stage (job-scoped) or via the video-CAS (video-scoped, F3 in P3), `emit_event`, advance
> `jobs.stage` (orchestrator is the sole writer of `jobs.stage`).

#### Task [BE] P2-W1: worker consumer + stage runner skeleton

**Files:** `worker/vtn_worker/main.py`, `worker/vtn_worker/runner.py`,
`tests/integration/test_runner.py`.

- [ ] `main.py`: `QueueProvider.receive()` loop → `runner.run(job_id, attempt)`; on success
  `complete`, on exception record `error_code/error_message`, emit `error`, and `complete` (or
  dead-letter after max attempts). Duplicate delivery safe (skip-if-present).
- [ ] `runner.run`: ordered stage list; orchestrator sets `jobs.stage` and emits `stage` events;
  parallel `analyzing` fork runs transcribe + visual concurrently (asyncio.gather) — the third branch,
  extract-style, is a no-op stub here and lands in P3 (F7) — and the orchestrator sets `analyzing` on
  entry and `segmenting` on join (branches never write `jobs.stage`); on completion set
  `status=review_ready`, emit `done`.
- [ ] Test: a job with all-fake stages reaches `review_ready`; `jobs.stage` only ever set by the
  orchestrator; a forced exception in one stage records error + emits `error` event.
- [ ] Run → PASS. `git commit -m "P2: worker consumer + stage runner"`

**Acceptance:** test exits 0; job reaches `review_ready`; the parallel fork keeps `jobs.stage` at
`analyzing` while emitting per-branch `stage` events. *(spec: Job state machine; The parallel
`analyzing` fork; Idempotency and resumability)*

#### Task [BE] F2-T1 (fake): resolving stage + canonical claim + dedup

**Files:** `packages/vtn_ingest/src/vtn_ingest/resolve.py`, `worker/.../stages/resolving.py`,
`tests/integration/test_resolving.py`.

- [ ] `SourceResolver` registry; `FakeResolver.can_handle/resolve` returns a deterministic
  `ResolvedSource`. Canonical claim: `pg_advisory_xact_lock(hashtext(canonical_url))` then
  `INSERT ... ON CONFLICT (canonical_url) DO NOTHING`; re-point `job.video_id` + delete placeholder
  if a canonical row exists, else promote own placeholder. Validate public/reachable → else
  `unsupported_url`/`video_unavailable` (fake can simulate both).
- [ ] Test: first job promotes its placeholder; a second job for the same canonical URL re-points to
  the existing video and deletes its placeholder; `uq_videos_canonical` never violated under two
  concurrent claims (run both in tasks).
- [ ] Run → PASS. `git commit -m "F2(fake): resolving + canonical dedup claim"`

**Acceptance:** test exits 0; two concurrent same-URL jobs end with exactly one canonical video row
and both jobs pointing at it. *(spec: URL resolution & ingestion; Re-submit dedup)*

#### Task [BE] F4/F5/F6-T1 (fake): media + transcript + visual stages

**Files:** `vtn_ingest/acquire.py`, `vtn_transcript/chain.py`, `vtn_visual/index.py`,
`worker/.../stages/{acquiring_media,transcribe,index_visual}.py`,
`tests/integration/test_analyze_fake.py`.

- [ ] `acquiring_media`: `FakeAcquirer.download_proxy` writes a tiny proxy blob, sets
  `videos.proxy_blob_path`; skip-if-present. `transcribe`: `FakeTranscriptProvider` → delete-before-
  insert `transcript_spans` for the `video_id`, record `source`. `index_visual`: `FakeFrameSampler`
  + `FakeOcr` → `visual_events` (with phash, ocr_text, frame_blob_path).
- [ ] Each stage emits its per-branch `stage` event; transcript ASR-fallback path emits a `warning`
  (fake can force it).
- [ ] Test: spans + visual_events written; `uq_spans_video_start`/`uq_visual_video_at_type` hold;
  ASR-fallback emits a `warning` event; re-run skips (idempotent).
- [ ] Run → PASS. `git commit -m "F4/F5/F6(fake): analyze stages"`

**Acceptance:** test exits 0; transcript+visual rows present and unique; ASR-fallback warning fires.
*(spec: analyzing — transcribe / index visual; Shared video artifact concurrency — delete-before-
insert)*

#### Task [BE] F8-T1 (fake): segmenting — signals + fusion + refinement

**Files:** `vtn_segment/{detectors.py,fusion.py,refine.py,context.py}`,
`worker/.../stages/segmenting.py`, `tests/unit/test_fusion.py`,
`tests/integration/test_segmenting_fake.py`.

- [ ] `BoundaryDetector` Protocol + `BoundaryCandidate` (spec types). `TimelineContext` interval-join
  (transcript windows ↔ visual events); duration-drift warning. Fusion: cluster within `merge_window`
  (4s), score `Σ weight*strength` (weights from `vtn_core.settings`), keep above `min_score`, snap to
  transcript-span starts / nearest slide frame. `refine.py`: `FakeChatModel.complete_json` returns
  refinement JSON (merge/drop/title/summary_seed/classification) keyed by index; schema-validated,
  one retry, fallback to unrefined boundaries + `warning` on invalid JSON. Persist `clips`
  (`status=pending`, title, summary_seed, classification, contiguous `order_index`).
- [ ] Unit test fusion scoring + clustering + snapping deterministically. Integration: clips
  persisted contiguous; refinement-fallback path on bad JSON emits `warning`; `assert_clips_
  contiguous_ordered` passes.
- [ ] Run → PASS. `git commit -m "F8(fake): segmenting"`

**Acceptance:** `uv run pytest tests/unit/test_fusion.py tests/integration/test_segmenting_fake.py
-q` exits 0; clips contiguous & unique; refinement fallback emits a warning, not a failure. *(spec:
Boundary signals; Fusion + LLM refinement)*

#### Task [BE] F9-T1 (fake): drafting — scene selection + clip summary

**Files:** `vtn_notes/{scene.py,summary.py}`, `worker/.../stages/drafting.py`,
`tests/unit/test_scene.py`, `tests/integration/test_drafting_fake.py`.

- [ ] `scene.py`: gather clip `visual_events`, score by `event_type` weight × confidence (boost
  slide/title/demo), dedup via phash Hamming distance (threshold from spike S3), pick best, set
  `scene_at_sec/scene_blob_path/scene_source='auto'`. `summary.py`: one `FakeChatModel.complete_json`
  per clip fed transcript + neighbor context + visual/OCR summary + chosen scene + `style_profile` +
  the **global outline** (all titles + summary_seeds); write `summary`, set `ai_summary=summary`,
  `status='ready'`, emit `clip.ready`. Bounded concurrency (`settings.drafting.max_concurrency`).
- [ ] Unit test scene scoring + phash dedup. Integration: every clip becomes `ready`, each emits one
  `clip.ready`; summaries reference outline context (fake echoes it).
- [ ] Run → PASS. `git commit -m "F9(fake): drafting"`

**Acceptance:** tests exit 0; each clip emits exactly one `clip.ready`; all clips `status=ready` with
a scene. *(spec: Scene selection; Clip summary generation)*

#### Task [BE] F10-T1: initial note assembly + baseline version (`review_ready`)

**Files:** `vtn_notes/assemble.py`, `worker/.../stages/assemble.py`,
`tests/integration/test_assemble.py`.

- [ ] `assemble_note(clips)` → markdown: per clip `## {order}. {title}` + time range + scene image
  (relative path) + `scene_caption` + `summary` prose; **never** transcript, **never** regen marker.
  Write `notes` row (`include_summary=true,include_transcript=false,is_polished=false,
  clips_dirty=false,built_from_version=1`), freeze `note_versions` `seq=1,kind=initial,
  is_baseline=true` with `clips_snapshot`. Set `status=review_ready`, emit `done`.
- [ ] Test: note assembled; `assert_note_no_transcript` + `assert_note_no_regen_marker` +
  `assert_note_content_flags` + `assert_baseline_immutable` pass; baseline snapshot contains the
  clip structure.
- [ ] Run → PASS. `git commit -m "F10: initial note assembly + baseline"`

**Acceptance:** test exits 0; invariants pass on the assembled note; exactly one baseline version.
*(spec: Initial note assembly; review_ready)*

#### Task [API] P2-A1: read endpoints `GET /jobs/{id}/clips` + `GET /jobs/{id}/note`

**Files:** `apps/api/vtn_api/routes/{clips,note}.py`, `tests/integration/test_reads.py`.

- [ ] `GET /clips` → ordered clips + per-clip ETag + collection ETag. `GET /note` →
  `{markdown,include_summary,include_transcript,is_polished,clips_dirty}` + note ETag. Both require
  the cookie.
- [ ] Test: after a fake run, both return the expected shapes + ETags.
- [ ] Run → PASS. `git commit -m "P2: read endpoints"`

**Acceptance:** test exits 0; ETags present and equal to the spec derivations. *(spec: API contract —
Clips, Note)*

#### Task [TEST-E2E-MOCK] P2-E1: submit → worker(fake) → review_ready → GET note

**Files:** `tests/e2e/test_submit_to_review.py`.

- [ ] Boot the API + run the worker in-process against **real Postgres + Azurite + in-memory queue +
  fake AI**. `POST /login`, `POST /jobs`, drain the queue through the runner, open SSE and collect
  events, then `GET /jobs/{id}` (`review_ready`), `GET /clips`, `GET /note`.
- [ ] Assert: event order `stage(resolving..drafting)` → N×`clip.ready` → `done`; clips contiguous;
  note passes all C5 invariants. **STRICT branch:** force the fake transcript to fail captions so
  the ASR-fallback `warning` event fires.
- [ ] Run → expect FAIL first (stages not wired), then PASS once the pipeline is complete.
- [ ] `git commit -m "P2: mocked e2e submit->review_ready"`

**Acceptance:** `uv run pytest tests/e2e/test_submit_to_review.py -q` exits 0; the ASR-fallback
warning is asserted (branch coverage); invariants pass. *(spec: Diagram 1; Event contract; Latency)*

**Phase P2 gate:** mocked e2e green; invariants pass on output; `--cov-fail-under=85` for touched
packages; independent-reviewer pass (does the fake pipeline satisfy spec stage order, event
contract, and the gating predicate?).

---

## P3 — Real media + AI adapters + style + cost

Swap real adapters in behind the P2 Protocol seams; add F3 (artifact CAS), F7 (style), F20 (cost),
and the **first real-infra e2e** (gated by P0-S0 credentials spike).

### [P3] Feature F3 — Shared video artifact concurrency

#### Task [BE] F3-T1: per-artifact CAS claim / wait / recover

**Files:** `vtn_storage/repos.py` (`claim_artifact`, `wait_ready`, `release_on_fail`,
`reclaim_stale`), `worker/.../stages/*` (wrap acquire/transcribe/visual),
`tests/integration/test_artifact_cas.py`.

- [ ] Implement the spec CAS: `UPDATE videos SET <a>_state='building',<a>_owner_job=:job WHERE
  id=:v AND <a>_state='absent' RETURNING id`. Winner builds + delete-before-insert + set `ready`;
  losers poll/`LISTEN` until `ready` then skip-if-present; failure resets to `absent`; stale
  `building` past `settings.stale_timeout` is reclaimable via the dated CAS.
- [ ] Test (real Postgres): two concurrent jobs on one video → exactly one builds each artifact, the
  other reads; killed winner (state left `building`, old timestamp) → reclaim succeeds and
  delete-before-insert prevents duplicates under `uq_*` indexes.
- [ ] Run → PASS. `git commit -m "F3: shared video artifact CAS"`

**Acceptance:** test exits 0; single-writer-per-canonical-video proven under contention; stale
takeover safe. *(spec: Shared video artifact concurrency)*

### [P3] Real adapters — F2/F4/F5/F6/F8/F9 real impls

#### Task [BE] F2/F4-T2 (real): YouTube/MSEvent/Generic resolvers + yt-dlp acquirer

**Files:** `vtn_ingest/resolvers/*.py`, `vtn_ingest/ytdlp_acquirer.py`,
`tests/integration/test_resolvers.py`, `tests/e2e-real/test_acquire_real.py`.

- [ ] Implement resolvers per spike S1 contract; `YtDlpAcquirer.download_proxy` with the locked
  format selector @720p → Blob; map yt-dlp errors to `unsupported_url`/`video_unavailable`.
- [ ] Integration: resolver `can_handle`/`resolve` for sample URLs (no network — use recorded
  metadata fixtures from S1). Real-infra e2e (opt-in): download a real 30s clip, assert proxy exists
  and is playable-sized.
- [ ] Run integration → PASS; run real with `-m real_infra` → PASS.
- [ ] `git commit -m "F2/F4(real): resolvers + yt-dlp"`

**Acceptance:** integration exits 0 offline; `uv run pytest -m real_infra -k acquire_real` exits 0
with credentials. *(spec: resolving; acquiring_media; spike S1)*

#### Task [BE] F5/F6-T2 (real): transcript chain + ffmpeg/OCR/pHash visual

**Files:** `vtn_transcript/providers/*.py`, `vtn_visual/{sampler.py,detectors.py,ocr.py,phash.py}`,
`tests/integration/test_visual_real_local.py`, `tests/e2e-real/test_transcript_real.py`.

- [ ] Transcript chain: SourceCaptions → YouTubeCaptions → AzureSpeech (per spike S4), normalize to
  spans, record `source`, ASR-fallback `warning`. Visual: two-tier ffmpeg sampling (spike S2),
  detectors (SSIM/diff/title-OCR/keyframe/demo/low-speech), Azure OCR (spike S5, failure → warning),
  pHash per frame (spike S3).
- [ ] Integration (local ffmpeg on a tiny bundled clip, OCR faked): events produced with phash; SSIM
  thresholds deterministic. Real-infra e2e: Azure Speech transcribes a 20s real clip; Azure OCR on a
  real slide returns text.
- [ ] Run → PASS (integration); `-m real_infra` → PASS.
- [ ] `git commit -m "F5/F6(real): transcript chain + ffmpeg/OCR/pHash"`

**Acceptance:** integration exits 0 (local ffmpeg, faked OCR); real-infra transcript+OCR exit 0 with
credentials; OCR failure path emits a `warning`. *(spec: transcribe; index visual; spikes S2–S5)*

#### Task [BE] F8/F9-T2 (real): Foundry chat + embeddings in refinement, drafting, semantic detector

**Files:** `vtn_ai/foundry.py` (`FoundryChatModel`, `FoundryEmbeddingModel`),
`vtn_segment/detectors.py` (`SemanticShiftDetector`), `tests/e2e-real/test_llm_real.py`.

- [ ] Implement `FoundryChatModel.complete_json` (structured output per spike S6, one retry on
  invalid JSON) and `FoundryEmbeddingModel.embed` (spike S7). Wire `SemanticShiftDetector` to
  embeddings. Model ids/params from `prompts.model_config`/settings (never hard-coded).
- [ ] Real-infra e2e: refinement + one clip summary against real Foundry on a tiny outline; assert
  schema-valid JSON; embeddings return the spike's dim.
- [ ] Run `-m real_infra` → PASS.
- [ ] `git commit -m "F8/F9(real): Foundry chat + embeddings"`

**Acceptance:** `uv run pytest -m real_infra -k llm_real` exits 0; outputs schema-valid; invalid-JSON
retry path covered by a mocked test. *(spec: Fusion + LLM refinement; Clip summary; spikes S6/S7)*

### [P3] Feature F7 — Style extraction & resolution

#### Task [BE] F7-T1: extract (LLM, cached) + resolve (deterministic depth-merge)

**Files:** `vtn_style/{extract.py,resolve.py}`, `worker/.../stages/extract_style.py`,
`style_defaults` repo, `tests/unit/test_style_resolve.py`,
`tests/integration/test_extract_style.py`.

- [ ] `extract`: LLM distill per-dimension (`style_descriptor`,`granularity`,`density`,
  `derived_prompt`) with confidence; cache on job; upsert `style_defaults.extracted` when
  `save_style_as_default`; schema-validated, fallback to depth + `warning` on failure. `resolve`
  (every job): per-dimension confident-example-wins else depth preset (Brief→coarse/low,
  Balanced→medium/medium, Thorough→fine/high, custom→medium/medium); persist `prompts.style_profile`;
  emit `style.resolved`.
- [ ] Unit: depth-only profile when no examples; example-wins when confident; thin example falls back.
  Integration: `style_profile` always populated before segmenting; `style.resolved` emitted;
  `assert_style_profile_valid` passes.
- [ ] Run → PASS. `git commit -m "F7: style extraction + resolution"`

**Acceptance:** tests exit 0; `style_profile` populated for jobs with and without examples; merge
rules match spec table. *(spec: extract style; 4b Style extraction; style_profile JSON)*

### [P3] Feature F20 — Cost model

#### Task [BE] F20-T1: estimate at submit + record actuals + `cost.estimate` event

**Files:** `vtn_core/cost.py`, hook into F1 (estimate) + runner (actuals),
`tests/integration/test_cost.py`.

- [ ] `estimate(duration, depth)` → `{usd, breakdown}` (expected clip count→LLM calls, transcript
  provider, OCR frame budget) stored at submit in `job_costs.estimate_json`. `resolving` refines and
  emits `cost.estimate`. After the run, record `actual_json` (tokens, audio-min, OCR frames). Warn,
  never block.
- [ ] Test: estimate stored at submit; `cost.estimate` emitted in `resolving`; actuals recorded post-
  run; the run never blocks on cost.
- [ ] Run → PASS. `git commit -m "F20: cost estimate + actuals"`

**Acceptance:** test exits 0; estimate present at submit, actuals after run, `cost.estimate` event
fired. *(spec: Cost model; Cost policy — warn never block)*

#### Task [TEST-E2E-REAL] P3-E1: tiny real video → review_ready against real Azure (opt-in)

**Files:** `tests/e2e-real/test_full_real.py` (tagged `-m real_infra`, OFF by default).

- [ ] **Depends on:** P0-S0 credentials spike green. Submit a tiny (~30s) real captioned video; run
  the worker with the **azure** profile (real Foundry/Speech/Vision/embeddings + real Blob; in-memory
  queue acceptable here, real Service Bus covered in P6). Assert: reaches `review_ready`; clips +
  note produced; **all C5 invariants pass**; transcript `source` recorded; cost actuals present.
  Asserts schema/happy-path; does NOT force rare branches (mocked tier owns those).
- [ ] Run `RUN_REAL=1 uv run pytest -m real_infra -k full_real` → PASS.
- [ ] `git commit -m "P3: real-infra e2e tiny video -> review_ready"`

**Acceptance:** OFF in the default suite; with `-m real_infra` + credentials it exits 0 against live
Azure and the output validates against C1/C5. **This is the only test proving live wiring; mocked
e2e does not substitute, and it does not substitute for the mocked tier's branch coverage.** *(spec:
Pipeline; Latency; Testing and evaluation)*

**Phase P3 gate:** integration (Postgres+Azurite+fake AI) green; real-infra e2e green with
credentials; independent-reviewer pass (real adapter shapes vs spike writeups; no model id
hard-coded; CAS correctness).

---

## P4 — Editing & reconciliation backend

All endpoints reach `review_ready`/`exported` only (`active` → `409 job_not_review_ready`). Auto-sync
vs needs_ack is driven by `notes.is_polished` (spec: Reconciliation). Every mutation guarded by the
correct ETag scope (C2).

### [P4] Feature F12 — Media serving

#### Task [API] F12-T1: proxy range stream + scene-candidates + frame-on-demand

**Files:** `apps/api/vtn_api/routes/media.py`, `tests/integration/test_media.py`.

- [ ] `GET /videos/{id}/stream` → HTTP range streaming from Blob. `GET /clips/{id}/scene-candidates`
  → a few auto-suggested frames (from `visual_events`). `POST /clips/{id}/scene {at_sec}` →
  frame-on-demand ffmpeg extract at `at_sec`, set scene (`scene_source='manual'` on explicit set),
  single-clip ETag guarded, return asset URL. Expired-proxy → degraded `warning`, not failure.
- [ ] Test: range request returns 206 + correct bytes slice; scene-candidates returns frames; set-
  scene extracts + updates clip + bumps ETag; stale ETag → `412`.
- [ ] Run → PASS. `git commit -m "F12: media serving + frame-on-demand"`

**Acceptance:** test exits 0; 206 partial content correct; set-scene is ETag-guarded. *(spec: Media;
Manual capture; Data retention — expired proxy degraded)*

### [P4] Feature F13 — Clip content edits (PATCH) + auto-sync + needs_ack

#### Task [API] F13-T1: `PATCH /clips/{id}` (title/summary/caption), ETag, auto-sync/needs_ack

**Files:** `apps/api/vtn_api/routes/clips.py`, `vtn_notes/assemble.py` (reuse),
`tests/integration/test_patch_clip.py`.

- [ ] Guard single-clip ETag (`If-Match`=clip `updated_at`); mismatch → `412 stale_write`. On first
  `summary` edit set `ai_summary` (if null); clearing `summary` restores from `ai_summary`.
  `scene_caption` is the **sole** caption owner (no `/note` caption). Flag logic: if
  `notes.is_polished=false` → **auto-sync** (re-assemble `notes.markdown` from current clips in the
  **same transaction**, both flags stay false, bump note ETag); if `is_polished=true` → `409
  needs_ack`, client re-sends `?ack=1` → freeze `auto_pre_change` version + set `clips_dirty=true`,
  then apply.
- [ ] Test: unpolished edit auto-syncs note (markdown reflects change, flags false); polished edit →
  409, then `?ack=1` freezes `auto_pre_change` + sets `clips_dirty`; stale ETag → 412; caption edit
  follows the same flow; `active` job → `409 job_not_review_ready`. Invariants pass after each.
- [ ] Run → PASS. `git commit -m "F13: PATCH clip + auto-sync/needs_ack"`

**Acceptance:** test exits 0; all four flag/ETag branches covered; `assert_reconciliation_flags`
passes. *(spec: PATCH /clips; Auto-sync rule; Caption editing; needs_ack)*

### [P4] Feature F14 — Structural edits (split / merge)

#### Task [API] F14-T1: `split` + `merge`, collection ETag, renumber, placeholder values

**Files:** `apps/api/vtn_api/routes/clips.py`, `vtn_notes/structural.py`,
`tests/integration/test_split_merge.py`.

- [ ] `POST /clips/{id}/split {at_sec}` (transcript-anchored) and `POST /clips/merge {clip_ids}`
  guarded by the **clips-collection ETag** (`max(updated_at)`); mismatch → 412. Derive post-split/
  post-merge field values **deterministically** per the spec table (title/summary/ai_summary/
  summary_seed/scene_*/classification/needs_regen=true/status=ready). Renumber `order_index` in one
  transaction preserving `UNIQUE(job_id,order_index)`. Then run the same auto-sync/needs_ack flow as
  F13.
- [ ] Test: split → two contiguous clips, second titled "… (cont.)", scene inheritance rule honored,
  both `needs_regen`; merge → concatenated summary, first clip's scene kept; renumber dense & unique;
  collection-ETag stale → 412; needs_ack path when polished. `assert_clips_contiguous_ordered` passes.
- [ ] Run → PASS. `git commit -m "F14: split/merge + placeholder values"`

**Acceptance:** test exits 0; placeholder values match the spec table exactly; renumber preserves the
unique constraint under a concurrent second structural edit (→412). *(spec: split/merge; Post-split/
post-merge clip values)*

### [P4] Feature F15 — Regenerate

#### Task [API] F15-T1: `POST /clips/{id}/regenerate`, single-clip ETag, clears needs_regen

**Files:** `apps/api/vtn_api/routes/clips.py`, `vtn_notes/summary.py` (reuse),
`tests/integration/test_regenerate.py`.

- [ ] Single-clip ETag guarded; re-run the per-clip summary generator; rewrite `summary`+`ai_summary`,
  clear `needs_regen`; same needs_ack/auto-sync flow as F13. Marker disappears (it's a projection of
  `needs_regen`) with no rewrite of stored markdown.
- [ ] Test: regenerate clears `needs_regen`, updates summary; stale clip ETag → 412; polished → 409
  needs_ack; unpolished → auto-sync; stored markdown never contains the regen marker.
- [ ] Run → PASS. `git commit -m "F15: regenerate"`

**Acceptance:** test exits 0; `needs_regen` cleared; `assert_note_no_regen_marker` passes after.
*(spec: regenerate endpoint; Assembled Markdown while needs_regen)*

### [P4] Feature F16 — Note editing (autosave + content selection)

#### Task [API] F16-T1: `PUT /note` (autosave, coalesced) + `PATCH /note` (content flags)

**Files:** `apps/api/vtn_api/routes/note.py`, `tests/integration/test_note_edit.py`.

- [ ] `PUT /note {markdown}` note-ETag guarded → set `is_polished=true`, coalesce an `auto_edit`
  version (debounced; skip if identical to latest). `PATCH /note {include_summary?,
  include_transcript?}` persists the **boolean(s) only** — never rewrites `notes.markdown`, never sets
  `is_polished`, but advances note ETag. A request that would leave **both** flags false →
  `422 validation_error` (at-least-one rule; DB CHECK is the backstop). Stale → 412.
- [ ] Test: autosave sets `is_polished`, coalesces versions (two quick edits → one `auto_edit`);
  setting `include_summary=false` (transcript still on) persists boolean only, markdown unchanged,
  `is_polished` unchanged; setting both false → 422; stale ETag → 412; `assert_note_no_transcript`
  + `assert_note_content_flags` still hold after each toggle.
- [ ] Run → PASS. `git commit -m "F16: note autosave + content selection flags"`

**Acceptance:** test exits 0; flags never mutate markdown or `is_polished`; both-false rejected with
422; autosave coalesces. *(spec: PUT/PATCH /note; Content selection is a render-time projection)*

### [P4] Feature F17 — Reconciliation (rebuild / keep)

#### Task [API] F17-T1: `note/rebuild` + `note/keep` + flag state machine

**Files:** `apps/api/vtn_api/routes/note.py`, `tests/integration/test_reconcile.py`.

- [ ] `POST /note/rebuild` (note-ETag) → re-assemble from current clips, `is_polished=false`,
  `clips_dirty=false`, freeze `auto_rebuild`, set `built_from_version`. `POST /note/keep` (note-ETag)
  → clear `clips_dirty` only (stays polished/drifted). Encode `assert_reconciliation_flags` for each
  op.
- [ ] Test: rebuild re-syncs markdown + clears flags + freezes `auto_rebuild`; keep clears only
  `clips_dirty`; stale ETag → 412. Replays the **worked example v1→v4** (edit→keep-editing→rebuild)
  asserting flags + version kinds at each step.
- [ ] Run → PASS. `git commit -m "F17: rebuild/keep + flag state machine"`

**Acceptance:** test exits 0; worked-example v1→v4 reproduced with correct `kind`s and flags. *(spec:
Edit ↔ Review reconciliation; Operations; Worked example)*

### [P4] Feature F18 — Versioning

#### Task [API] F18-T1: list / save (both-ETag) / restore (both-ETag, non-destructive)

**Files:** `apps/api/vtn_api/routes/versions.py`, `vtn_notes/versions.py`,
`tests/integration/test_versions.py`.

- [ ] `GET /versions` ordered. `POST /versions {label?}` → snapshot note+clips (`manual`); requires
  **both** note ETag + clips-collection ETag (comma-sep); either stale → 412; does not advance
  ETags. `POST /versions/{seq}/restore` → freeze current as `restore` first (non-destructive), then
  apply snapshot's note+clips; `note_settings` restores `is_polished`+`include_summary`+
  `include_transcript` verbatim (always valid per at-least-one), `clips_dirty` always recomputed to
  false; requires **both** ETags; `version_not_found` → 404.
- [ ] Test: save requires both ETags (one stale → 412); restore is non-destructive (current frozen
  first) and itself undoable; restore sets `clips_dirty=false`; restoring a polished/drifted snapshot
  reproduces `is_polished=true,clips_dirty=false`; `assert_baseline_immutable` holds; unknown seq →
  404.
- [ ] Run → PASS. `git commit -m "F18: versioning save/restore"`

**Acceptance:** test exits 0; both-ETag guard enforced on save+restore; restore non-destructive +
clips_dirty recomputed. *(spec: Versioning; Restore semantics; API contract — Versions)*

### [P4] Feature F19 — Export

#### Task [API] F19-T1: `POST /export` ZIP + render-time projections + metadata

**Files:** `vtn_export/{markdown.py,zip.py,metadata.py}`, `apps/api/vtn_api/routes/export.py`,
`tests/integration/test_export.py`.

- [ ] Assemble ZIP from current persisted state. **`note.md` section body chosen by
  `include_summary`** (spec: Export format): when `true`, `notes.markdown` with relative image paths;
  when `false`, a bare per-clip **scaffold** (heading + time range + scene + `scene_caption`, no
  prose) built from current clips (stored `notes.markdown` left untouched). On top, **render-time
  projections composited from current clips** (regen marker for `needs_regen` clips; transcript
  blockquote from `transcript_spans` when `include_transcript=true`) — never read from stored
  markdown. `images/NNNN-slug.png` one per clip; `metadata.json` (source URL, depth/resolved
  profile, transcript source, per-clip+per-scene timestamps). `status='exported'`, repeatable,
  **does not lock editing**. Record `exports` row.
- [ ] Test: ZIP passes `assert_export_structure`; **summary-only + no flags** → `note.md` equals
  stored markdown (paths rewritten); **transcript-only** (`include_summary=false,
  include_transcript=true`) → `note.md` has scaffold + transcript, **no prose**, and stored
  `notes.markdown` is unchanged; **both** → prose + transcript; with a `needs_regen` clip the marker
  appears in `note.md` but not in stored markdown; a second export after an edit re-assembles;
  `status='exported'` does not block a subsequent clip edit.
- [ ] Run → PASS. `git commit -m "F19: export ZIP + projections"`

**Acceptance:** test exits 0; `assert_export_structure` passes; projections composited at serialize
time only; export repeatable + non-locking. *(spec: Export format; Editing is gated until
review_ready — exported is not a lock)*

#### Task [TEST-E2E-MOCK] P4-E2: full edit→review→export round-trip

**Files:** `tests/e2e/test_edit_review_export.py`.

- [ ] Extend P2-E1: after `review_ready`, exercise PATCH clip (auto-sync), split (placeholder +
  needs_ack after a prose edit), regenerate (clears marker), rebuild, save+restore version, content
  selection (export each of summary-only / transcript-only / both and assert the body differs while
  stored markdown is unchanged; both-false → 422), export. Assert flags/versions/ETags at each step
  and invariants on every materialized note + the export ZIP. STRICT branches: 412 on stale ETag,
  409 needs_ack, 409 job_not_review_ready, 422 both-content-flags-false.
- [ ] Run → PASS. `git commit -m "P4: mocked e2e edit/review/export"`

**Acceptance:** `uv run pytest tests/e2e/test_edit_review_export.py -q` exits 0; all error branches
fire; invariants pass throughout. *(spec: Diagram 1 EDIT/REVIEW rect; API contract)*

**Phase P4 gate:** mocked e2e (P2-E1 + P4-E2) green; `--cov-fail-under=85`; independent-reviewer pass
(ETag scopes correct per endpoint; reconciliation flag transitions vs spec; export projection source
of truth).

---

## P5 — Frontend

Five App Router routes (spec: Frontend), reference `frontend-design/high-fidelity/v2/*`. API client +
SSE client in `apps/web/lib`. Component tests (Vitest) + Playwright e2e against a mocked backend.

### File map

- `apps/web/lib/{api.ts,sse.ts,types.ts,markdown.ts}`
- `apps/web/app/{login,submit,edit/[jobId],review/[jobId],export/[jobId]}/page.tsx`
- `apps/web/components/{timeline,inspector,doc-editor,content-selector,version-history,cost-banner}/*`
- `apps/web/e2e/journey.spec.ts`

### [P5] Feature F21 — Login

#### Task [FE] F21-T1: login form + route gating
**Files:** `app/login/page.tsx`, `lib/api.ts`, `__tests__/login.test.tsx`.
- [ ] Form → `POST /login`; on success route to `/submit`; on 401 show envelope message.
  Middleware/guard redirects unauthenticated route access to `/login`.
- [ ] Test: submit calls login; 401 shows error; guarded route redirects.
- [ ] `git commit -m "F21: login"`
**Acceptance:** `pnpm test login` exits 0; unauthenticated access redirects. *(spec: Login)*

### [P5] Feature F22 — Submit

#### Task [FE] F22-T1: submit form + depth chooser + examples + cost banner
**Files:** `app/submit/page.tsx`, `components/cost-banner/*`, `__tests__/submit.test.tsx`.
- [ ] URL input; depth chooser (Thorough/Balanced/Brief/"I'll prompt it"+custom field); "Match my
  style" panel (saved style or `.md` upload, ≤size cap, `.md` only; save-as-default toggle);
  non-blocking cost banner from the `202` estimate. Submit → `POST /jobs` → navigate to
  `/edit/{job_id}`.
- [ ] Test: custom depth reveals prompt field; non-`.md`/oversize upload rejected client-side; submit
  navigates with the returned job_id; cost banner renders the estimate (warn, never block).
- [ ] `git commit -m "F22: submit"`
**Acceptance:** `pnpm test submit` exits 0; validation + navigation covered. *(spec: Submit; Input
validation; Cost policy)*

### [P5] Feature F23 — Edit page (timeline + progressive SSE)

#### Task [FE] F23-T1: SSE consumer + progressive lanes + gated tools
**Files:** `lib/sse.ts`, `app/edit/[jobId]/page.tsx`, `components/timeline/*`,
`__tests__/edit-sse.test.tsx`.
- [ ] SSE client with `Last-Event-ID` reconnect; four lanes (Screenshot/Clips/Transcript/Summary)
  that fill per the spec readiness table as `stage`/`clip.ready` arrive; "preparing" indicator;
  tools (Split/Merge/Set scene/clip edits) disabled until `done`/`status∈{review_ready,exported}`.
- [ ] Test (mock EventSource): lanes reveal in order on staged events; `clip.ready` fills a clip
  skeleton; tools stay disabled until `done`; reconnect replays from `Last-Event-ID`.
- [ ] `git commit -m "F23: edit SSE + progressive lanes"`
**Acceptance:** `pnpm test edit-sse` exits 0; gating + reconnect covered. *(spec: Edit page; Editing
is gated; Event contract)*

#### Task [FE] F23-T2: split / merge / set-scene / regenerate + inspector + note-refresh modal
**Files:** `components/timeline/*`, `components/inspector/*`, `__tests__/edit-tools.test.tsx`.
- [ ] Split at playhead, merge selection, set-scene (frame-on-demand + candidate frames), inspector
  edits title/summary with "Restore AI summary", Regenerate on `needs_regen` clips. ETag-aware calls;
  on `409 needs_ack` show the heads-up modal ("Keep editing" → retry `?ack=1`; "Cancel" aborts). On
  `412 stale_write` **do NOT auto-retry**: refetch the latest clip/collection state, surface a visible
  "changed elsewhere — review and reapply" notice with the refreshed values, and require the user to
  explicitly reapply/confirm the edit against the new state (the reapplied write uses the fresh ETag).
  This preserves the design's optimistic-concurrency guarantee — a 412 can never be silently
  overwritten. "Note will refresh" chip shown ⇔ about to change clips while polished.
- [ ] Test: needs_ack modal flow retries with `ack=1`; **412 refetches and surfaces the stale-state
  notice and sends NO write until the user reapplies/confirms** (assert zero automatic mutation after
  a 412), then the user-confirmed reapply uses the refreshed ETag; restore-AI-summary resets prose;
  regenerate clears the needs-regen marker in the UI.
- [ ] `git commit -m "F23: edit tools"`
**Acceptance:** `pnpm test edit-tools` exits 0; needs_ack + 412 + restore flows covered. *(spec: Edit
page; reconciliation warnings are pure functions of flags)*

### [P5] Feature F24 — Review page

#### Task [FE] F24-T1: doc editor + caption edit + content selector + version history + rebuild banner
**Files:** `app/review/[jobId]/page.tsx`, `components/doc-editor/*`, `components/content-selector/*`,
`components/version-history/*`, `__tests__/review.test.tsx`.
- [ ] Render assembled note (heading+range+scene figure with **editable caption via clip PATCH**;
  prose shown when `include_summary`; optional **read-only** transcript blockquote when
  `include_transcript`); Markdown toolbar; autosave (debounced `PUT /note`, note-ETag). **Content
  selector** — Summary / Transcript / Both — backed by `PATCH /note {include_summary?,
  include_transcript?}` (booleans only); the control **disables deselecting the last** option
  (at-least-one) and surfaces the server `422` defensively. When `include_summary=false` the prose
  editor stays available but marked "excluded from output". Version history popover (Save/Restore,
  both-ETag); rebuild banner ⇔ `clips_dirty=true` (Rebuild/Keep).
  **Decision (record in plan):** editor = textarea + live preview for MVP (TipTap deferred — see
  Open questions).
- [ ] Test: autosave debounces + sends note-ETag; caption edit calls clip PATCH (not /note); content
  selector persists booleans only and re-renders without rewriting prose; transcript-only hides prose
  in the preview but keeps the editor; the selector won't let both be deselected; rebuild banner
  appears on `clips_dirty`; restore needs both ETags.
- [ ] `git commit -m "F24: review page"`
**Acceptance:** `pnpm test review` exits 0; caption-via-clip + content-selector (booleans only,
at-least-one) + rebuild banner covered. *(spec: Review; Caption editing; Content selection is a
render-time projection; Versioning)*

### [P5] Feature F25 — Export page

#### Task [FE] F25-T1: summary card + ZIP contents + download
**Files:** `app/export/[jobId]/page.tsx`, `__tests__/export.test.tsx`.
- [ ] Summary card (filename, section/screenshot counts, size), ZIP contents listing, download →
  `POST /export` → `download_url`; "Start a new note" → `/submit`.
- [ ] Test: download calls export and follows `download_url`; counts render.
- [ ] `git commit -m "F25: export page"`
**Acceptance:** `pnpm test export` exits 0. *(spec: Export page)*

#### Task [TEST-E2E] P5-E1: Playwright login→submit→edit→review→export (mocked backend)
**Files:** `apps/web/e2e/journey.spec.ts`.
- [ ] Mock the API (MSW or a stub server) including an SSE stream; drive the full journey; assert
  lanes fill, tools unlock on `done`, an edit triggers note refresh, a polished edit shows the modal,
  export downloads a ZIP.
- [ ] Run `pnpm e2e` → PASS. `git commit -m "P5: playwright journey"`
**Acceptance:** `pnpm e2e` exits 0; full journey green against the mocked backend. *(spec: Frontend ↔
backend flow)*

**Phase P5 gate:** component tests + Playwright journey green; `pnpm test --coverage` ≥80%;
independent-reviewer pass (UI ↔ event contract; gating predicate; caption/toggle source of truth).

---

## P6 — Infra, CI/CD, eval, real queue, docs

### [P6] Feature F26 — Infrastructure as code (one-command up/down)

> **Goal: a single `azd up` provisions every Azure resource and deploys the API + worker + web, and
> a single `azd down` tears everything back down.** `azd` (Azure Developer CLI) is the one-command
> wrapper — plain `az` (Azure CLI) has no `up`/`down`. `az` is still used inside hooks/CI for
> fine-grained steps, but the operator-facing lifecycle is exactly two commands.

#### Task [INFRA] F26-T1: Bicep modules + `azure.yaml` wired for `azd up`/`azd down`
**Files:** `infra/main.bicep`, `infra/main.parameters.json`, `infra/modules/*.bicep`, `azure.yaml`,
`tests/infra/test_bicep.sh`.
- [ ] Bicep for ACA env (API app + worker job), Service Bus (queue+DLQ), PostgreSQL Flexible Server,
  Storage (`proxy`/`frames`/`exports`/`examples` containers), Key Vault (cred hash + cookie secret),
  App Insights, AI Foundry/Speech/Vision; Managed Identity service-to-service; no secrets in config.
- [ ] `azure.yaml` declares all three deployable services (`web`, `api`, `worker`) with their
  Dockerfiles + ACA targets so `azd up` builds, provisions (Bicep), and deploys in one command.
  Parameterize env (dev/staging/prod) via `infra/main.parameters.json` + `azd env`.
- [ ] Test: `az bicep build infra/main.bicep` exits 0; `azd provision --preview` (what-if) validates
  with no errors.
- [ ] `git commit -m "F26: bicep + azure.yaml for azd up/down"`
**Acceptance:** `az bicep build infra/main.bicep` exits 0; `azd provision --preview` validates; every
resource in the architecture diagram is declared. *(spec: Deployment and CI/CD; Security and
configuration)*

#### Task [INFRA] F26-T2: one-command lifecycle — `azd up` brings up, `azd down` tears down
**Files:** `azure.yaml` (postprovision/postdeploy hooks), `infra/hooks/{migrate,seed_secrets}.sh`,
`docs/deploy.md`, `tests/infra/test_lifecycle.sh` (opt-in, real subscription).
- [ ] A `postprovision`/`postdeploy` hook runs `alembic upgrade head` against the provisioned
  Postgres and writes the credential hash + cookie secret into Key Vault, so `azd up` yields a
  **working** environment (login succeeds, a job can be submitted) with no manual steps. `azd down
  --purge --force` removes every resource group + purges soft-deleted Key Vault/AI resources.
- [ ] Test (opt-in, `RUN_REAL=1` against a throwaway subscription/RG): `azd up` exits 0 and a
  smoke check (`GET /healthz` 200, `POST /login` 200) passes; then `azd down --purge --force` exits 0
  and a follow-up `az group show` confirms the RG is gone.
- [ ] `git commit -m "F26: one-command azd up/down lifecycle"`
**Acceptance:** with credentials, `azd up` provisions+deploys a working env in one command and
`azd down --purge --force` removes everything (verified by `az group show` failing afterward). OFF in
CI/default; documented in `docs/deploy.md`. *(spec: Deployment and CI/CD)*

#### Task [TEST-E2E-REAL] F26-T3: full journey against the DEPLOYED `azd up` environment (opt-in)
**Depends on:** F26-T2 (`azd up` yields a working env), P0-S0 credentials spike. **This is distinct
from P3-E1/P6-E1**, which run the worker locally against real Azure *services*; this one drives the
**actually deployed** API + worker + Service Bus + Postgres + Blob over the public endpoint that
`azd up` produced — the only test that proves the provisioned-and-deployed stack works end to end.
**Files:** `tests/e2e-real/test_deployed_journey.py` (tagged `-m real_infra`, OFF by default),
`tests/infra/test_lifecycle.sh` (sequences up → this test → down).
- [ ] Resolve the deployed API base URL from `azd env get-values` (e.g. `API_BASE_URL`). Against that
  live endpoint with real credentials: `POST /login`; `POST /jobs` with a tiny (~30s) real captioned
  video; consume the **real SSE** stream until `done`/`review_ready`; `GET /clips` + `GET /note`;
  exercise one clip edit (auto-sync) and `POST /export`; download the ZIP. Assert **all C5
  invariants** on the note + export, the transcript `source` is recorded, and progress events flowed
  worker→DB→SSE over the deployed path. Schema/happy-path only — do not force rare branches (the
  mocked tier owns those).
- [ ] Wire `tests/infra/test_lifecycle.sh` to run **`azd up` → `RUN_REAL=1 uv run pytest -m real_infra
  -k deployed_journey` → `azd down --purge --force`** in sequence, so teardown always runs even if the
  test fails (trap/finally).
- [ ] Run the sequenced lifecycle with credentials → PASS. `git commit -m "F26-T3: deployed-env real e2e"`
**Acceptance:** OFF in the default suite; with credentials, `tests/infra/test_lifecycle.sh` exits 0 —
`azd up` deploys, the deployed-journey `[TEST-E2E-REAL]` passes against the live public endpoint, and
`azd down --purge --force` removes everything (verified by `az group show` failing afterward). **This
is the API-level proof that the deployed stack works; P3-E1/P6-E1 do not substitute (they run the
worker locally), and the browser-level proof is F26-T4.** *(spec: Architecture; Deployment and CI/CD;
Diagram 1 frontend↔backend flow)*

#### Task [TEST-E2E-REAL] F26-T4: browser journey against the DEPLOYED frontend → deployed backend (opt-in)
**Depends on:** F26-T2, P5-E1 (the Playwright journey spec exists), P0-S0 credentials spike. **This
closes the one seam no other test covers:** P5-E1 drives the real browser UI but against a *mocked*
backend; F26-T3 hits the *real deployed* backend but at the API level, not through the browser. This
task drives the **real deployed frontend through a real browser against the real deployed backend** —
the actual click-through-the-live-site path (CORS, cookies over the real domain, SSE over the public
endpoint).
**Files:** `apps/web/e2e/journey.deployed.spec.ts` (reuses the P5-E1 journey, base URL from env,
tagged so it is OFF by default), `tests/infra/test_lifecycle.sh` (the same up→tests→down sequence).
- [ ] Parameterize the Playwright `baseURL` from `DEPLOYED_WEB_URL` (resolved via `azd env
  get-values`); reuse the P5-E1 journey steps (login → submit a tiny real video → watch lanes fill via
  real SSE → one edit → review → export → download ZIP) with **no backend mocking** — assertions
  relaxed to schema/happy-path (real timing), not deterministic branch coverage.
- [ ] Add it to `tests/infra/test_lifecycle.sh` so the sequence is **`azd up` → F26-T3 (API) →
  F26-T4 (browser) → `azd down --purge --force`** (teardown in trap/finally, always runs).
- [ ] Run the sequenced lifecycle with credentials → PASS. `git commit -m "F26-T4: deployed browser e2e"`
**Acceptance:** OFF by default; with credentials, the browser journey passes against the live deployed
site (`DEPLOYED_WEB_URL`) end to end. Together F26-T3 (API) + F26-T4 (browser) prove the deployed app
is e2e running from both the API and the UI. *(spec: Frontend; Diagram 1 frontend↔backend flow)*

### [P6] Feature F27 — CI/CD

#### Task [CI] F27-T1: GitHub Actions CI (lint/type/test/build) + CD (migrate/deploy)
**Files:** `.github/workflows/{ci.yml,cd.yml}`.
- [ ] CI: ruff + mypy + `pytest` (unit+integration+e2e against fake profile, Postgres+Azurite service
  containers) with `--cov-fail-under=85`; `pnpm lint test e2e`; build web/api/worker images.
  Real-infra tests excluded (no `-m real_infra` in CI). CD: push images, `alembic upgrade head`
  before traffic, `azd deploy`. Environments: dev/staging + prod via Bicep params.
- [ ] Verify on a PR: CI green; CD dry-run plan renders.
- [ ] `git commit -m "F27: CI/CD workflows"`
**Acceptance:** CI workflow green on a PR (all gates incl. coverage); CD runs `alembic upgrade head`
as a step. *(spec: Deployment and CI/CD)*

### [P6] Feature — Azure Service Bus QueueProvider (real)

#### Task [BE] F-SB-T1: `ServiceBusQueue` + DLQ + duplicate-safe receive
**Files:** `vtn_storage/servicebus.py`, `tests/e2e-real/test_servicebus.py`.
- [ ] Implement `QueueProvider` over Azure Service Bus per spike S8 (send/receive/complete/
  dead_letter, `job_id`+`attempt`, lock renewal, duplicate-safe). Real-infra e2e (opt-in): round-trip
  + poison message → DLQ.
- [ ] Run `-m real_infra` → PASS. `git commit -m "F-SB: Service Bus QueueProvider"`
**Acceptance:** `uv run pytest -m real_infra -k servicebus` exits 0; poison → DLQ. *(spec: Queue
abstraction; Reliability — Queue retries + DLQ)*

### [P6] Feature F28 — Segmentation eval harness

#### Task [BE] F28-T1: labeled-talk recall/precision report vs config weights
**Files:** `eval/segmentation/{run.py,labels/*.json}`, `tests/unit/test_eval_metrics.py`.
- [ ] Load labeled boundary sets, run fusion at configured `segmentation.weights`/granularity, score
  recall/precision (boundary match within a tolerance window), emit a report; weights stay in config.
- [ ] Unit test the metric on a tiny labeled fixture (known recall/precision).
- [ ] `git commit -m "F28: segmentation eval harness"`
**Acceptance:** `uv run python eval/segmentation/run.py` emits a recall/precision report;
`test_eval_metrics` exits 0. *(spec: Testing and evaluation — Segmentation eval harness)*

#### Task [TEST-E2E-REAL] P6-E1: full real-infra e2e incl. real Service Bus (opt-in)
**Files:** `tests/e2e-real/test_full_real_bus.py`.
- [ ] Extend P3-E1 to enqueue via real Service Bus and run the worker as a separate process. Assert
  the same invariants + that progress events flow worker→DB→SSE.
- [ ] Run `-m real_infra` → PASS. `git commit -m "P6: full real-infra e2e w/ Service Bus"`
**Acceptance:** `uv run pytest -m real_infra -k full_real_bus` exits 0 against live Azure. *(spec:
Architecture; Reliability)*

### [P6] Feature F29 — README & top-level docs

**Boundary:** the repo's front-door `README.md` (+ `docs/deploy.md` cross-link). **NOT** per-package
internal docs. **Depends on:** F26 (deploy commands), P2–P5 (local-run commands) all real.

#### Task [DOCS] F29-T1: `README.md` — overview, architecture, run-locally, deploy, test, repo map
**Files:** `README.md`, `tests/docs/test_readme.py`.
- [ ] Write `README.md` covering: **what the app does** (one-paragraph product summary from spec:
  Overview); **architecture** (the spec: Architecture diagram + the worker→DB→SSE→browser flow, who-
  never-calls-whom); **run locally** (`docker compose up -d`, `uv sync`, `alembic upgrade head`, start
  API + worker + `pnpm dev`, the `fake` profile for zero-spend offline runs); **deploy** (the
  one-command **`azd up`** to provision+deploy and **`azd down --purge`** to tear down — link
  `docs/deploy.md`); **test** (the layer commands from "Test layers", incl. the `-m real_infra`
  opt-in); **repo map** (the `apps/`, `worker/`, `packages/vtn_*`, `infra/`, `migrations/` table from
  spec: Repository structure); and a config/secrets note (env locally, Key Vault in cloud).
- [ ] Every command in the README is **copy-pasteable and verified** against the actual scripts; no
  `TODO`/placeholder. Cross-link the spec and this plan.
- [ ] Test: `tests/docs/test_readme.py` asserts `README.md` exists and contains the required section
  headings (Overview, Architecture, Run locally, Deploy, Test, Repo map) and the literal strings
  `azd up` and `azd down`; lints fenced command blocks for the known command prefixes (`uv `,
  `pnpm `, `docker compose `, `azd `).
- [ ] Run → PASS. `git commit -m "F29: README + top-level docs"`
**Acceptance:** `uv run pytest tests/docs/test_readme.py -q` exits 0; a new contributor can follow
"Run locally" to a working local stack and "Deploy" is exactly `azd up` / `azd down`. *(spec:
Overview; Architecture; Repository structure; Deployment and CI/CD; Local dev)*

### [P6] Final real-infra acceptance run (the end-of-build "is it actually running?" gate)

> The real-infra tests stay OFF by default throughout the build (cost/credentials). This is the
> **one mandatory point where they all run for real**, at the very end, as the definitive sign-off
> that the app runs end to end against real Azure — not just that mocked tests are green.

#### Task [TEST-E2E-REAL] P6-FINAL: run the whole opt-in real-infra suite once, up→test→down
**Depends on:** every other P6 task green. **Files:** `tests/infra/test_lifecycle.sh` (final form),
`docs/acceptance.md` (records the run).
- [ ] Execute the full sequence once with real credentials against a throwaway subscription/RG:
  **`azd up`** → `RUN_REAL=1 uv run pytest -m real_infra` (the entire opt-in suite: adapter live-wiring
  checks, P3-E1, P6-E1, the deployed API journey F26-T3, the deployed browser journey F26-T4) →
  **`azd down --purge --force`**. Teardown runs in a trap/finally so it always fires.
- [ ] Record in `docs/acceptance.md`: date, region, the deployed URLs, the test summary (pass counts),
  the actual cost from `job_costs.actual_json`, and a one-line "app is e2e running" attestation.
- [ ] Run → PASS; resources confirmed gone (`az group show` fails). `git commit -m "P6-FINAL: real-infra acceptance run"`
**Acceptance:** the full `-m real_infra` suite exits 0 in one sequenced run, the deployed app served
the real user journey from **both API (F26-T3) and browser (F26-T4)**, and teardown left nothing
behind. `docs/acceptance.md` records the evidence. **This task is the explicit end-of-build proof that
the implemented app is e2e running against real infrastructure.** *(spec: Testing and evaluation;
Architecture; Deployment and CI/CD)*

**Phase P6 gate (final gate of the build):** CI green; eval report produced; `README.md` present,
accurate, and its doc-test green; **and the final real-infra acceptance run (P6-FINAL) is green —
`azd up` → full `-m real_infra` suite (incl. deployed API journey F26-T3 + deployed browser journey
F26-T4) → `azd down --purge` — with `docs/acceptance.md` recording the evidence**; final
independent-reviewer pass over the whole system vs spec (gap-pass checklist below).

---

## Gap pass (predict-the-diff) — results

Ran 2 rounds against the templates checklist. Outcome:

- ✅ Plan is Phase → Feature → Task; full feature list (F0–F29 + F-SB) with disjoint boundaries; each
  feature assigned to a phase; no feature depends on a later phase.
- ✅ **One-command infra lifecycle:** `azd up` provisions+deploys and `azd down --purge` tears down
  (F26-T2), verified by an opt-in real-subscription lifecycle test.
- ✅ **Top-level docs:** `README.md` (F29) covers overview/architecture/run-locally/deploy/test/repo
  map, with a doc-test gate; deploy is exactly `azd up` / `azd down`.
- ✅ Every spec capability maps to exactly one feature (coverage table). Cross-cutting groundwork
  (scaffold, models, migration, contracts, fakes, invariants, spikes) is in P0/P1 as task groups,
  not features.
- ✅ **Migrations + rollback:** P1-T2 verifies `upgrade`+`downgrade`; CD runs `alembic upgrade head`.
- ✅ **Null/empty/zero states:** empty-list version history, no-results clips, expired-proxy degraded,
  depth-only style profile (no examples), summary-only export == verbatim markdown, transcript-only
  export (prose excluded, scaffold body), both-content-flags-false → 422 — each has a task.
- ✅ **Error/timeout/retry at every external seam:** ASR fallback, refinement fallback, OCR failure →
  warning; yt-dlp → `unsupported_url`/`video_unavailable`; queue DLQ; LLM invalid-JSON retry — owned
  by the mocked e2e (STRICT) and spikes.
- ✅ **Integration seams:** auth×SSE (cookie), browser-never-calls-worker, exact serialization at SSE
  frames + ZIP, ETag scopes per endpoint — all explicit.
- ✅ **Idempotency/concurrency:** per-`job_id`+stage skip-if-present; video-level CAS (F3); canonical
  claim advisory lock (F2); `UNIQUE(job_id,order_index)` renumber under contention (F14); both-ETag
  guards (F18) — all tested against real Postgres.
- ✅ Contracts referenced by tasks; no per-task redefinition (point at spec); names/types pinned in C1.
- ✅ Acceptance criteria are runnable commands/assertions, not adjectives.
- ✅ **Both e2e tiers:** mocked (P2-E1, P4-E2, P5-E1; on by default; owns branch coverage) + real-infra
  (P3-E1, P6-E1, F-SB, real-adapter tasks; `-m real_infra` OFF by default; owns live wiring), gated
  by P0-S0 credentials spike, scheduled early (P3).
- ✅ **Deployed-environment e2e (API + browser):** F26-T3 runs a full `[TEST-E2E-REAL]` API journey
  against the live endpoint produced by `azd up`, and F26-T4 runs the same journey through a real
  browser (deployed frontend → deployed backend), closing the only uncovered seam; both sequenced
  `azd up → tests → azd down` (teardown always runs).
- ✅ **Mandatory end-of-build real-infra acceptance:** P6-FINAL runs the entire `-m real_infra` suite
  once (`azd up` → all real tests → `azd down`) and records evidence in `docs/acceptance.md` — the
  explicit proof the app is e2e running against real infra, even though real tests stay OFF by default
  during the build.
- ✅ Every external dependency has a spike (S0–S9); C4 contracts derived from them.
- ✅ Shared invariant module (C5) called from every test layer + every real run + export.
- ✅ Independent-reviewer gate at each phase gate, after the test gates.
- ✅ Measurable completion gate: `--cov-fail-under=85` (py) / 80% (web) wired into CI.
- ✅ Each task cites spec section(s); source-of-truth order named at top.
- ✅ No scope creep — anything beyond the spec moved to Open questions.
- ✅ **Prerequisites checklist** upfront (local tools/versions, Docker daemon, ffmpeg, cloud auth +
  roles + secrets), each with a verification command, grouped local vs real-infra/deploy.
- ✅ **Implementation checklist (task tracker)** with one checkbox per task (every task ID) + a
  phase-gate roll-up box per phase, for post-implementation done/not-done tracking.

No task required a 3rd gap round (none over-large enough to split further at plan altitude). The
finest TDD decomposition (literal per-cycle code) is produced at execution time per task block; the
representative code shown here is sufficient to predict the diff.

---

## Open questions (do not invent answers)

Two kinds, both deferring to the design — never overriding it: **(a) genuine spec gaps** the design
leaves open (items 1–2: editor tech, local secret bootstrap), each naming the section that should
answer it plus the minimum decision to unblock; and **(b) design-deferred decisions** the spec's own
*Open questions* already parks with a stated default (items 3–7) — listed here only so they are not
silently re-litigated or added. Where the design already states a default, that default stands; these
are not gaps to fill.

1. **Markdown editor component (Review).** Spec: Review says "Markdown toolbar" but not the editor
   tech. *Decision to unblock F24:* MVP uses textarea + live preview; TipTap/ProseMirror is a
   follow-up. (Recorded as a decision in F24-T1; flag for review.)
2. **Auth secret bootstrap locally.** Spec: Security puts the credential hash + cookie secret in Key
   Vault; local dev needs an env equivalent. *Decision to unblock F0:* read from `.env` locally,
   Key Vault in cloud (documented in `.env.example`). Confirm acceptable.
3. **Proxy retention window length** and explicit "re-acquire" vs new job — spec: Open questions
   (deferred). Affects F12 degraded state copy only; default: no auto-expiry in MVP.
4. **Vision-LLM frame understanding** (deep multimodal) — spec: Open questions (deferred). Not built;
   CV+OCR only. Listed so it is not silently added.
5. **Fusion weights / granularity as user controls** — spec: Open questions (config-only for now).
   F28 keeps them in config; no UI surface.
6. **Version-history pruning policy** for very long histories — spec: Open questions (baseline always
   retained). MVP: no pruning. Confirm.
7. **Web PubSub vs LISTEN/NOTIFY at scale** — spec: Progress event transport notes NOTIFY may be
   limiting. MVP uses LISTEN/NOTIFY; Web PubSub is a drop-in behind the same SSE API if needed.

---

## Hand-off

Plan approved → execute in a **fresh session** via `superpowers:executing-plans` or
`superpowers:subagent-driven-development`, reading only this plan + the spec. Start at P0; do not
proceed past a phase gate until its tests + independent-reviewer pass are green.
