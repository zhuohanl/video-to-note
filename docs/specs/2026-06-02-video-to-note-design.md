# Video-to-Note Design

> Status: detailed / implementation-ready draft. Supersedes the high-level design of the
> same date. Forks decided during brainstorming are recorded in **Decided defaults**.
> Deepened (2026-06-02) with: fusion/alignment algorithm, cost model, latency budgets,
> review mutation semantics, and auth/SSE/local-dev/migrations.

## Overview

Video-to-Note is a single-user, Azure-first web application that turns public conference
session videos into reviewed markdown notes with screenshots. The first target sources are
YouTube, Microsoft Build, and Microsoft Ignite session URLs. The first output is a
downloadable ZIP containing a markdown file and screenshot assets referenced by relative
paths.

The product is optimized for a personal learning workflow. It produces detailed, editable
drafts for sessions the user is learning from, while still supporting lighter summaries. The
system drafts automatically, then **requires human review before export** so the user can
fix missed screenshots, section boundaries, and note detail.

To keep perceived latency low, the pipeline **streams sections into the review UI as soon as
each is drafted** (progressive review). The user can begin reviewing early sections while
later ones are still being generated.

## Goals

- Accept public YouTube, Microsoft Build, and Microsoft Ignite video URLs.
- Generate markdown notes with relevant, deduplicated screenshots.
- Support note depth choices: Thorough, Balanced, Brief, and custom prompting.
- Automatically process mixed session formats (slide talks, demos, Q&A, speaker changes,
  visually dense sections) without asking the user to classify the session.
- Provide a review UI for editing notes, adjusting sections, regenerating a single section,
  and capturing missing screenshots at arbitrary timestamps before export.
- Stream draft results progressively to minimize perceived latency.
- Deploy as an Azure-first production-style application with frontend, backend, worker,
  infrastructure, CI/CD, observability, and secure configuration.
- Keep AI providers behind adapters so non-Azure services can be benchmarked/swapped when
  they materially improve quality (especially image/video/multimodal).

## Non-goals for v1

- Multi-user workspaces, sharing, comments, or permissions.
- Fully unattended batch processing of many videos.
- Direct publishing to GitHub, OneDrive, SharePoint, or a team knowledge base.
- Real-time processing while a session is still live.
- Pixel-perfect note formatting for every downstream markdown tool.

---

## Decided defaults

These forks were resolved during brainstorming and are binding for v1:

| Area | Decision |
| --- | --- |
| Result delivery | **Progressive review** — sections stream to the UI as drafted. |
| Streaming transport | **Server-Sent Events (SSE)** for job progress and section events. |
| Segmentation | **Hybrid** — uniform signal interface + config weights (recall), single LLM refinement pass (precision/labeling). |
| Heuristic extensibility | Few general detectors behind one interface; per-speech variation handled by the LLM refinement prompt, not by growing rules. |
| Media acquisition | **Download once** (yt-dlp), sample frames locally with ffmpeg; store a proxy copy in Blob. |
| Manual capture | **Backend frame-on-demand** — review streams the stored video; capture calls ffmpeg to extract the exact frame at a timestamp. |
| Note generation granularity | **One LLM call per section** (enables progressive streaming + per-section regeneration). |
| Screenshot dedup | Perceptual hashing (pHash) to drop near-duplicate frames. |
| Frontend | React + Next.js (App Router). |
| Backend/worker | Python; FastAPI for the API, shared packages for ingestion/media/AI/export. |
| Queue | Azure Service Bus with dead-letter queue. |
| Metadata store | Azure PostgreSQL Flexible Server. |
| Model access | Azure AI Foundry by default; provider adapters for non-Azure benchmarking. |
| Embeddings | Azure OpenAI embedding deployment (via Foundry) for semantic-shift detection. |
| Auth | Single shared username/password (hash in Key Vault) → signed httpOnly **session cookie**; SSE authenticates via the cookie automatically. |
| Cost policy | **Warn, never block** — estimate up front, show it, always proceed; record actuals. |
| Latency target | **Time-to-first-section (TTFS) ≤ ~1–2 min** for a 1-hr captioned video; captions-first is the latency lever. |
| Queue abstraction | `QueueProvider` interface — Azure Service Bus in cloud, in-memory/SQLite queue locally. |
| Migrations | **Alembic**, versioned in repo; `alembic upgrade head` as a CD step. |
| Local dev | `docker-compose` (Postgres + Azurite) + a `fake` AI provider profile for offline, zero-spend runs. |
| Re-submit dedup | Reuse a video's proxy + transcript artifacts across jobs when `canonical_url` already processed; always create a new job. |

---

## Architecture

```text
                 ┌────────────┐        ┌──────────────────────┐
  Browser  ◄────►│  Frontend  │◄──SSE──│        API           │
 (Next.js)       │  (Next.js) │  REST  │   (FastAPI, ACA app) │
                 └────────────┘        └──────────┬───────────┘
                                                  │ enqueue job
                                                  ▼
                                        ┌──────────────────────┐
                                        │  Azure Service Bus    │
                                        │  (jobs + dead-letter) │
                                        └──────────┬───────────┘
                                                  │ trigger
                                                  ▼
                                        ┌──────────────────────┐
                                        │  Worker               │
                                        │ (ACA Job, Python)     │
                                        │  yt-dlp / ffmpeg /    │
                                        │  AI adapters          │
                                        └──┬───────────┬───────┘
                                           │           │
                          ┌────────────────┘           └───────────────┐
                          ▼                                            ▼
                 ┌──────────────────┐                       ┌─────────────────────┐
                 │ Azure Blob       │                       │ Azure PostgreSQL    │
                 │ (video proxy,    │                       │ (jobs, sections,    │
                 │  frames, exports)│                       │  notes, screenshots)│
                 └──────────────────┘                       └─────────────────────┘

 Cross-cutting: Key Vault (secrets + shared credential hash + cookie-signing secret),
                Managed Identity (service-to-service auth), Application Insights (telemetry),
                Azure AI Foundry (models + embeddings), Azure AI Speech / Vision / Document Intelligence.
                User-facing auth: a single shared login → signed httpOnly session cookie.
```

### Component responsibilities

- **Frontend (Next.js App Router)**: submit form, progress view (SSE consumer), review editor
  (section list, markdown editor, video scrubber, screenshot tray), export trigger/download.
- **API (FastAPI on Azure Container Apps)**: validates submissions, creates `videos`/`jobs`
  rows, enqueues work, exposes job/section/screenshot/export endpoints, relays progress via
  SSE, serves stored video range requests and frame-on-demand, builds export ZIPs.
- **Worker (Azure Container Apps Job, Python)**: the pipeline. Consumes a Service Bus message,
  runs stages, writes artifacts to Blob and rows to PostgreSQL, and emits progress events the
  API forwards over SSE.
- **Service Bus**: decouples API from worker; provides retry + dead-letter.
- **Blob Storage**: video proxy, extracted frames/screenshots, markdown drafts, export ZIPs.
- **PostgreSQL**: relational, timeline-ordered metadata and review edit history.

### End-to-end sequence

1. User submits URL + note settings. API creates `video` + `job` (stage=`queued`) and
   enqueues a Service Bus message containing `job_id`.
2. Worker picks up the message, transitions stages, and persists artifacts.
3. As each section is drafted, the worker writes the `section` + `section_note` rows and
   publishes a `section.ready` progress event.
4. Frontend, subscribed via SSE, renders sections as they arrive.
5. User reviews/edits, optionally regenerates sections or captures frames (synchronous API
   calls, not the worker).
6. User exports. API assembles the ZIP from current DB state + Blob assets and returns a
   download URL.

### Progress event transport

The worker cannot hold the browser's HTTP connection, so progress flows:

`worker → progress channel → API SSE endpoint → browser`.

The progress channel is a dedicated PostgreSQL table (`job_events`, append-only) plus
PostgreSQL `LISTEN/NOTIFY`. The API's SSE endpoint `LISTEN`s on a per-job channel and streams
new `job_events` rows. This avoids adding Redis for v1 while giving near-real-time push. (If
NOTIFY proves limiting, swap to Azure Web PubSub behind the same SSE-facing API.)

---

## Pipeline stages (overview)

The worker runs a fixed sequence of stages (the job state machine below). Each stage owns one
shared package and writes timestamped artifacts that later stages consume. This section is the
conceptual map; exact algorithms are in **Pipeline (detailed algorithms)** further down.

| Stage | Package | What it does |
| --- | --- | --- |
| `resolving` | `vtn_ingest` | Resolve + validate the URL, fetch metadata, pick a source adapter; reuse artifacts if this video was processed before. |
| `acquiring_media` | `vtn_ingest` | Download one capped-resolution **proxy** copy (yt-dlp/ffmpeg). The proxy is the single source of truth for all later frame work and review scrubbing. |
| `transcribing` | `vtn_transcript` | Produce timestamped `transcript_spans` from captions (preferred) or Azure Speech ASR (fallback). |
| `indexing_visual` | `vtn_visual` | Extract timestamped `visual_events` (slide/title/demo/keyframe…) from sampled frames. Runs **in parallel** with `transcribing`. |
| `segmenting` | `vtn_segment` | Turn transcript + visual signals into section boundaries: deterministic fusion (recall) → single LLM refinement pass (precision + titles/gists/labels). |
| `drafting` | `vtn_notes` | Per section: select + dedup screenshots, then generate the markdown note (one LLM call per section), emitted progressively. |
| `review_ready` | — | All sections drafted; awaiting human review. |
| `exported` | `vtn_export` | Assemble the ZIP (markdown + images + metadata). |

### A note on the word "indexing"

`indexing_visual` (and "transcript indexing") do **not** build a searchable / vector index, and
there is no semantic-search feature in v1. Both are **signal-extraction passes** that emit
timestamped rows feeding `segmenting`. In particular, the transcript embeddings exist only so
the `SemanticShiftDetector` can spot a cosine-similarity drop between adjacent windows (a
boundary signal) — not to answer queries.

### Transcript signals vs. visual signals

The two pre-segmentation stages produce different kinds of timestamped signal on the **same
clock** (both derive from the one downloaded proxy):

| | Transcript (`vtn_transcript` + SemanticShift) | Visual (`vtn_visual`) |
| --- | --- | --- |
| Raw material | Caption / ASR text spans | Sampled video frames |
| Technique | **Embeddings** → cosine drop between windows | **Pixel diff / SSIM + OCR**; no embeddings, no vector store |
| Emits | `semantic_shift` / `speaker_change` / `time_gap` candidates | `visual_events`: `slide_change` / `title_change` / `demo_change` / `keyframe` / `low_speech_visual` |
| Second job | — | Also the **candidate pool for screenshots** (drafting stage) |

`vtn_visual` therefore does double duty: its events are both boundary hints *and* the source of
the screenshots themselves. v1 deliberately does **no deep multimodal frame understanding** (no
CLIP-style frame embeddings, no vision-LLM slide description) — it is intentionally cheap CV +
targeted OCR, two-tier sampled to bound cost and latency. Upgrading this (Azure AI Video
Indexer, Gemini multimodal) is tracked in **Open questions**.

---

## Repository structure

```text
video-to-note/
├─ apps/
│  ├─ web/                      # Next.js frontend
│  │  ├─ app/                   # App Router routes
│  │  ├─ components/
│  │  ├─ lib/                   # api client, SSE client, types
│  │  └─ ...
│  └─ api/                      # FastAPI service
│     ├─ vtn_api/
│     │  ├─ main.py
│     │  ├─ routes/             # submit, jobs, sections, screenshots, media, export
│     │  ├─ sse.py
│     │  └─ deps.py
│     └─ pyproject.toml
├─ worker/                      # ACA Job entrypoint
│  ├─ vtn_worker/
│  │  ├─ main.py                # service bus consumer + stage runner
│  │  └─ stages/
│  └─ pyproject.toml
├─ packages/                    # shared Python libraries
│  ├─ vtn_core/                 # domain models, job state machine, settings
│  ├─ vtn_ingest/               # url resolvers, media acquisition
│  ├─ vtn_transcript/           # transcript providers (captions, speech)
│  ├─ vtn_visual/               # frame sampling, change/OCR/keyframe detectors
│  ├─ vtn_segment/              # signal interface, fusion, LLM refinement
│  ├─ vtn_notes/                # note generation, prompt templates, screenshot selection
│  ├─ vtn_export/               # markdown + ZIP assembly
│  ├─ vtn_storage/              # blob + postgres repositories, QueueProvider (Service Bus | local)
│  └─ vtn_ai/                   # provider adapters (Foundry, Speech, Vision, embeddings) + `fake` profile
├─ migrations/                  # Alembic env + versioned revisions
├─ fixtures/                    # canned transcript/visual/LLM outputs for the `fake` AI profile + tests
├─ infra/                       # Bicep modules + azure.yaml (azd)
├─ docker-compose.yml           # local Postgres + Azurite
├─ .github/workflows/           # CI/CD
└─ docs/specs/
```

Module boundaries map 1:1 to pipeline stages so each stage is independently testable. The
worker orchestrates packages; packages never import the worker.

---

## Domain model and job lifecycle

A **job** is one processing run for one **video** with one set of **prompt settings**.

### Job state machine

```text
queued
  → resolving        (resolve + validate URL, fetch metadata)
  → acquiring_media  (download proxy video)
  → transcribing     (captions or speech)            ─┐ run concurrently
  → indexing_visual  (frame sampling, change/OCR/kf)  ─┘
  → segmenting       (signal detection → fusion → LLM refinement)
  → drafting         (per-section notes + screenshot selection, emitted progressively)
  → review_ready     (all sections drafted; awaiting human review)
  → exported         (ZIP produced)

Terminal/side states:
  failed             (stage recorded; resumable)
  canceled
```

`transcribing` and `indexing_visual` both depend only on `acquiring_media` and run in
parallel. `segmenting` joins them. Each transition is persisted; `failed` records the stage so
a retry resumes from the last completed artifact rather than re-downloading or re-transcribing.

### Idempotency and resumability

- Every stage writes its output to Blob/PostgreSQL with a deterministic key derived from
  `job_id` + stage. Re-running a stage overwrites its own outputs only.
- Stage runner checks for an existing valid artifact before doing work (skip-if-present),
  enabling cheap resume after transient failures.
- Service Bus messages carry `job_id` + `attempt`; the worker is safe to receive duplicates.

---

## Data model (PostgreSQL)

Types are PostgreSQL. `id` columns are `uuid` (default `gen_random_uuid()`). Timestamps are
`timestamptz`. Time offsets within a video are `numeric(10,3)` seconds.

```sql
-- A submitted source video (one per resolved canonical URL is encouraged but not enforced).
CREATE TABLE videos (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_url      text NOT NULL,
  canonical_url   text,
  source_type     text NOT NULL,         -- 'youtube' | 'msbuild' | 'msignite' | 'other'
  title           text,
  duration_sec    numeric(10,3),
  proxy_blob_path text,                  -- stored video proxy for review scrubbing
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- One processing run.
CREATE TABLE jobs (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id      uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  stage         text NOT NULL DEFAULT 'queued',
  status        text NOT NULL DEFAULT 'active',  -- 'active' | 'failed' | 'review_ready' | 'exported' | 'canceled'
  error_code    text,
  error_message text,
  attempt       int  NOT NULL DEFAULT 0,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_jobs_video ON jobs(video_id);

-- Note settings captured at submission time.
CREATE TABLE prompts (
  job_id        uuid PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
  depth         text NOT NULL,           -- 'thorough' | 'balanced' | 'brief' | 'custom'
  custom_prompt text,                    -- non-null only when depth='custom'
  model_config  jsonb NOT NULL DEFAULT '{}'  -- externalized model ids/params
);

-- Normalized transcript spans on the video timeline.
CREATE TABLE transcript_spans (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id    uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  start_sec   numeric(10,3) NOT NULL,
  end_sec     numeric(10,3) NOT NULL,
  text        text NOT NULL,
  speaker     text,
  source      text NOT NULL              -- 'source_captions' | 'youtube_captions' | 'azure_speech'
);
CREATE INDEX idx_spans_video_time ON transcript_spans(video_id, start_sec);

-- Visual events detected from sampled frames.
CREATE TABLE visual_events (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id    uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  at_sec      numeric(10,3) NOT NULL,
  event_type  text NOT NULL,            -- 'slide_change' | 'title_change' | 'keyframe' | 'demo_change' | 'low_speech_visual'
  confidence  real NOT NULL,
  ocr_text    text,
  phash       text,                     -- perceptual hash for dedup
  frame_blob_path text
);
CREATE INDEX idx_visual_video_time ON visual_events(video_id, at_sec);

-- Sections produced by fusion/refinement (written progressively).
CREATE TABLE sections (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id         uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  order_index    int  NOT NULL,
  start_sec      numeric(10,3) NOT NULL,
  end_sec        numeric(10,3) NOT NULL,
  title          text,
  gist           text,                  -- one-line summary; feeds the cross-section continuity outline
  classification text,                  -- 'text_led' | 'visual_led' | 'mixed'
  confidence     real,
  status         text NOT NULL DEFAULT 'pending', -- 'pending' | 'drafting' | 'ready' | 'edited'
  UNIQUE (job_id, order_index)
);
CREATE INDEX idx_sections_job ON sections(job_id, order_index);

-- Generated + edited markdown per section, with revision history.
CREATE TABLE section_notes (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  section_id    uuid NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
  revision      int  NOT NULL DEFAULT 1,
  markdown_draft text,                  -- last AI-generated version
  markdown_edited text,                 -- user override; null until edited
  gen_settings  jsonb NOT NULL DEFAULT '{}',
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (section_id, revision)
);

-- Screenshots attached to a section.
CREATE TABLE screenshots (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  section_id   uuid NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
  at_sec       numeric(10,3) NOT NULL,
  asset_blob_path text NOT NULL,
  source       text NOT NULL,           -- 'auto' | 'manual'
  caption      text,
  selected     boolean NOT NULL DEFAULT true,
  order_index  int NOT NULL DEFAULT 0
);
CREATE INDEX idx_shots_section ON screenshots(section_id, order_index);

-- Append-only progress/event log; drives SSE via LISTEN/NOTIFY.
CREATE TABLE job_events (
  id         bigserial PRIMARY KEY,
  job_id     uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  type       text NOT NULL,            -- 'stage' | 'cost.estimate' | 'section.ready' | 'warning' | 'error' | 'done'
  payload    jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_events_job ON job_events(job_id, id);

-- Export records.
CREATE TABLE exports (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id      uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  zip_blob_path text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Cost estimate (at submit) and actuals (after run) per job. Warn-only; never blocks.
CREATE TABLE job_costs (
  job_id        uuid PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
  estimate_usd  numeric(10,4),
  estimate_json jsonb NOT NULL DEFAULT '{}',  -- per-component breakdown at submit
  actual_usd    numeric(10,4),
  actual_json   jsonb NOT NULL DEFAULT '{}',  -- recorded usage: tokens, audio-min, OCR frames
  computed_at   timestamptz
);
```

Regenerating one section inserts a new `section_notes` revision and never touches sibling
sections, satisfying "regenerate one section without invalidating the whole job."

---

## API contract

Base path `/api/v1`. JSON unless noted. A single shared username/password gates all routes via
a signed httpOnly **session cookie** (see Security). Errors use a consistent envelope:
`{ "error": { "code": "...", "message": "...", "stage": "..." } }`.

### Auth

```http
POST /api/v1/login   { "username": "...", "password": "..." }
→ 200  Set-Cookie: vtn_session=<signed>; HttpOnly; Secure; SameSite=Lax
→ 401  { "error": { "code": "invalid_credentials", ... } }   # rate-limited

POST /api/v1/logout  → 204   # clears the session cookie
```

All routes below require a valid session cookie; the SSE stream authenticates with the same
cookie automatically (no Authorization header needed).

### Submit and jobs

```http
POST /api/v1/jobs
{
  "url": "https://www.youtube.com/watch?v=...",
  "depth": "thorough" | "balanced" | "brief" | "custom",
  "custom_prompt": "string (required iff depth=custom)"
}
→ 202 { "job_id": "uuid", "video_id": "uuid", "cost_estimate": { "total_usd": 1.42, "breakdown": {...} } }
```

```http
GET /api/v1/jobs/{job_id}
→ 200 { job, video, prompt, stage, status, sections_summary }
```

```http
GET /api/v1/jobs/{job_id}/events        # SSE stream
Content-Type: text/event-stream
# event types: stage, cost.estimate, section.ready, warning, error, done
# replays missed events using Last-Event-ID, then live-streams
```

```http
POST /api/v1/jobs/{job_id}/cancel  → 200
```

### Sections, notes, screenshots (review)

```http
GET    /api/v1/jobs/{job_id}/sections                 → [section + current note + screenshots]
PATCH  /api/v1/sections/{id}                           # title/boundaries/markdown_edited
       # uses If-Unmodified-Since / revision guard → 412 on stale write (optimistic concurrency)
POST   /api/v1/sections/{id}/regenerate                # body: optional instruction override
                                                       # new revision; prior edited revision kept in history
GET    /api/v1/sections/{id}/revisions                 → [revision metadata, newest first]
POST   /api/v1/sections/{id}/revisions/{rev}/restore   # appends a new revision copying {rev}'s content
POST   /api/v1/sections/{id}/split  { "at_sec": n }    # see Review mutation semantics
POST   /api/v1/sections/merge       { "ids": [a,b] }   # see Review mutation semantics

POST   /api/v1/sections/{id}/screenshots/capture { "at_sec": n }
       # API ffmpeg-extracts frame from stored proxy → new screenshot row
PATCH  /api/v1/screenshots/{id}                        # caption/selected/order_index
DELETE /api/v1/screenshots/{id}
```

### Media (review scrubbing + frame capture)

```http
GET /api/v1/videos/{video_id}/stream     # HTTP Range requests over the stored proxy
GET /api/v1/screenshots/{id}/raw         # PNG bytes
```

### Export

```http
POST /api/v1/jobs/{job_id}/export   → 200 { "export_id": "...", "download_url": "..." }
GET  /api/v1/exports/{id}/download  → application/zip
```

Regenerate/split/merge during review are **synchronous API operations** that call the same
shared packages the worker uses (e.g. `vtn_notes.generate_section`); they do not go through
Service Bus, keeping review interactions snappy. On regenerate, the continuity context (global
outline + concept ledger) is rebuilt from the job's sibling sections' current titles/notes, so
a single regenerated section stays consistent with the rest.

---

## Pipeline (detailed algorithms)

All stages live in `worker/stages` and call shared packages.

### 1. URL resolution & ingestion (`vtn_ingest`)

- A registry of `SourceResolver` adapters, each exposing
  `can_handle(url) -> bool` and `resolve(url) -> ResolvedSource{canonical_url, source_type,
  title, duration, caption_tracks, media_locator}`.
- Adapters: `YouTubeResolver`, `MicrosoftEventResolver` (Build/Ignite session pages),
  `GenericResolver` (fallback).
- Validates the video is public and reachable; otherwise fail with
  `unsupported_url` / `video_unavailable`.
- **Re-submit dedup**: after resolving `canonical_url`, if a `videos` row already exists with a
  present `proxy_blob_path` (and transcript spans), reuse those artifacts and only create a new
  `job` — the media-acquisition and transcript stages skip straight to skip-if-present. This cuts
  both cost and latency on re-runs of the same session with different note settings.

### 2. Media acquisition (`vtn_ingest`)

- Download a single proxy copy via yt-dlp (or the source's media URL) at a capped resolution
  (default 720p) to bound storage/egress while keeping screenshots legible.
- Store as `videos.proxy_blob_path`. Skip-if-present for resume.
- The proxy is the **single source of truth** for both automated frame sampling and review
  scrubbing/manual capture (same pixels everywhere).

### 3. Transcript acquisition (`vtn_transcript`)

Priority chain, each behind a `TranscriptProvider`:
1. `SourceCaptionsProvider` — official captions/transcript from the source page.
2. `YouTubeCaptionsProvider` — YouTube captions.
3. `AzureSpeechProvider` — Azure AI Speech batch/fast transcription from the proxy audio.

Output normalized to `transcript_spans` (timestamped, speaker where available). The chosen
`source` is recorded and surfaced in review (no silent quality downgrade).

### 4. Visual-event indexing (`vtn_visual`)

This is signal extraction, not a search index (see **Pipeline stages → A note on the word
"indexing"**): no embeddings, no vector store — classic CV + OCR over sampled frames.

- Sample frames with ffmpeg. Two-tier sampling for latency: coarse pass (e.g. 1 fps) to find
  change regions, fine pass only around detected changes.
- Detectors (each emits `visual_events`):
  - **Slide/scene change**: frame difference / SSIM threshold.
  - **Title/OCR change**: OCR on candidate frames (Azure AI Vision or Document Intelligence;
    adapter-pluggable) → text-change detection.
  - **Keyframe candidate**: stable representative frame within a shot.
  - **Demo/visual-dense**: high local change rate (UI/code/animation).
  - **Low-speech/high-visual-change**: visual change in transcript-sparse windows.
- Compute a perceptual hash (`phash`) per stored frame for later dedup.

### 5. Boundary signals — uniform interface (`vtn_segment`)

The extensibility core. Every detector implements:

```python
class BoundaryDetector(Protocol):
    name: str
    def detect(self, ctx: TimelineContext) -> list[BoundaryCandidate]: ...

@dataclass
class BoundaryCandidate:
    at_sec: float
    signal_type: str      # 'semantic_shift' | 'speaker_change' | 'time_gap'
                          # | 'slide_change' | 'title_change' | 'demo_change'
    strength: float       # 0..1
    evidence: dict        # detector-specific, for debugging/eval
```

`TimelineContext` exposes the aligned transcript spans + visual events. Detectors:
- `SemanticShiftDetector` (embedding cosine drop between adjacent transcript windows; uses the
  Azure OpenAI embedding deployment),
- `SpeakerChangeDetector`, `TimeGapDetector`,
- `SlideChangeDetector`, `TitleChangeDetector`, `DemoChangeDetector` (derived from
  `visual_events`).

**Adding a new variation = register one detector or tune a weight**, never edit fusion.

**Alignment is a temporal interval-join, not an ML problem.** Both streams already share one
clock: transcript timestamps and frame timestamps both come from the *same downloaded proxy
file*. Building `TimelineContext` is therefore:
1. Slice the transcript into sliding windows (~20–40s / N spans).
2. For each window, attach the `visual_events` whose `at_sec` falls inside it (interval join).

Edge case: when transcript comes from *source captions* (a separate file rather than yt-dlp's
own captions), verify the caption duration matches the proxy. yt-dlp captions and ffmpeg frames
share the clock (drift = 0); a separate caption file can drift if the source was trimmed/
re-encoded. On detected drift, emit a `warning` — never silently misalign.

### 6. Fusion + LLM refinement (`vtn_segment`)

Deterministic fusion for **recall**, LLM for **precision/labeling**:

1. Collect all `BoundaryCandidate`s.
2. Cluster candidates within a `merge_window` (default 4s) into a combined boundary at the
   strength-weighted mean timestamp, carrying the *set* of contributing `signal_type`s.
3. Score each boundary: `score = Σ (weight[signal_type] * strength)`. Weights live in config
   (`segmentation.weights`) and are tunable from the eval harness — not code.
4. Keep boundaries above `min_score`; this yields candidate sections (favoring recall).
5. **Snap** each surviving boundary to the nearest transcript-span *start* and, where one is
   close, the nearest `slide_change` frame. This stops cuts landing mid-sentence and makes each
   section open on the slide that introduced it — which directly improves screenshot selection.
6. **LLM refinement pass** (single call). Input is a compact **outline**, never the full
   transcript: per candidate section → index, `start`/`end`, a short excerpt (first/last
   sentences + keywords), slide OCR text, contributing signal types, and visual-event counts.
   The LLM may: merge over-segmented neighbors, drop spurious boundaries, split a section *only
   at an anchor timestamp it was given* (so it cannot fabricate a time), write a title and a
   one-line gist, and classify each as `text_led | visual_led | mixed`. It returns strict JSON
   keyed by input index so results map back to timestamps. The titles + gists form the **global
   outline** that drives cross-section continuity at note-generation time (stage 8). This
   absorbs per-speech variation rules cannot.
   - **Robustness**: low temperature; schema-validated output; on invalid JSON, one retry, then
     fall back to the unrefined deterministic boundaries with a quality `warning` — never a hard
     failure.
   - **Token budget**: the common case (≤ ~40 candidate sections) is a single call. If the
     outline exceeds the budget, chunk it into contiguous section ranges with a small overlap
     and stitch the results.
7. Persist `sections` in order.

### 7. Screenshot selection (`vtn_notes`)

Per section:
1. Gather `visual_events` within `[start_sec, end_sec]`.
2. Score by `event_type` weight × `confidence`, boosting slide/title/diagram/demo frames.
3. Deduplicate via `phash` Hamming distance (drop near-identical frames).
4. Select top-N by depth: Thorough ≈ up to 1 per ~30–45s of visual content, Balanced fewer,
   Brief minimal. `visual_led` sections get a higher cap than `text_led`.
5. Store selected frames as `screenshots(source='auto')`.

### 8. Note generation (`vtn_notes`) — one call per section

- Optional whole-transcript cleanup pass first (fix ASR punctuation/casing) for `azure_speech`
  source; cached and reused per section.
- For each section, in `order_index` order with bounded concurrency, call the section
  generator with: section transcript, small neighbor context, visual/OCR summary, selected
  screenshot captions/timestamps, the **continuity context** (below), and the depth template or
  custom prompt.
- **Cross-section continuity** (avoid repeating content across sections):
  - *Primary, deterministic, parallel-safe* — a **global section outline** is available before
    any note generation begins (titles + classification + a one-line gist per section, produced
    by the fusion/refinement step). Every section call receives this outline, so each draft
    knows what was introduced earlier and what later sections will cover, without depending on
    other sections' generated prose. This works under bounded concurrency and out-of-order
    completion because the outline is computed up front.
  - *Refinement (best-effort)* — a compact **concept ledger** (key terms/claims already drafted)
    accumulates as sections finish; when a section starts, it also receives the ledger entries
    of any already-completed predecessors. It never blocks on in-flight predecessors, so it
    stays deterministic and non-serializing.
  - The continuity instruction: *assume the reader proceeds in order; define a concept the first
    time it appears, but reference (don't re-explain) concepts the outline shows were introduced
    in an earlier section.* This refines "self-contained" to mean **self-contained but not
    redundant**.
- Prompt templates (in `vtn_notes/prompts/`), one per depth, all sharing guardrails:
  preserve technical detail, clear headings, reference screenshots by relative path, **do not
  invent claims unsupported by transcript/visual evidence**, keep each section self-contained
  but not redundant (see continuity, above).
- Write `section_notes(revision=1, markdown_draft=...)`, set `sections.status='ready'`, and
  publish a `section.ready` event → streamed to the UI.

### 9. Progressive emission

Sections are emitted as each finishes generation (not in a final batch), so the review UI
fills in top-to-bottom. When the last section is ready, the job moves to `review_ready` and a
`done` event is sent.

---

## Frontend (Next.js App Router)

### Routes

- `/` — Submit page.
- `/jobs/[jobId]` — Progress + review (same route; progress view morphs into review as
  sections stream in).
- `/jobs/[jobId]/export` — export confirmation/download (or a modal on the review page).

### Submit page

- Prominent URL input with explicit placeholder.
- Note-depth cards: **Thorough / Balanced / Brief / I will prompt it**, each with a `?` help
  expander. Custom prompt textarea shown **only** for "I will prompt it", with example text.
- Submit → `POST /jobs` → navigate to `/jobs/[jobId]`.

### Progress → review (streaming)

- On mount, open SSE to `/jobs/{id}/events` (with `Last-Event-ID` resume).
- A stage indicator shows: resolving → acquiring → transcribing/indexing → segmenting →
  drafting. On each `section.ready`, append/patch that section in local state and render it
  immediately — the user can scroll and start editing while later sections arrive.
- `warning` events (e.g. "transcript from speech, not official captions") render as
  non-blocking banners. `error` shows an actionable failure with retry.
- The `cost.estimate` event renders an "Est. ~$X" banner (recolored if a soft ceiling is set);
  it is informational only and never blocks the job.

### Review editor — components

- `SectionList` — ordered sections; per section: title (editable), classification badge,
  timestamp range, markdown editor, screenshot tray, actions (Regenerate, Split, Merge-up,
  Revisions). Regenerating an edited section warns first; a Revisions menu lists prior versions
  with one-click restore. Split/Merge show the "boundaries changed — regenerate to fit" banner.
- `MarkdownEditor` — edit `markdown_edited`; live preview; debounced `PATCH`.
- `VideoScrubber` — HTML5 player sourced from `/videos/{id}/stream` (Range requests); shows
  section markers; "Capture frame here" → `POST /sections/{id}/screenshots/capture`.
- `ScreenshotTray` — thumbnails; toggle `selected`, edit caption, reorder, delete.
- `ExportBar` — triggers export, shows download link.

### State management

- Server state via React Query (jobs, sections, screenshots) keyed by `job_id`.
- SSE updates patch the React Query cache (optimistic where safe).
- Edits are mutations with optimistic updates + rollback on error.

---

## Latency strategy

- **Parallelize** `transcribing` and `indexing_visual` (both depend only on media).
- **Two-tier frame sampling** so visual indexing scans coarsely first, refining only around
  changes.
- **Bounded-concurrency per-section generation** so multiple sections draft at once while
  still emitting progressively in order.
- **Progressive review** so time-to-first-section, not total job time, is what the user feels.
- **Capped proxy resolution** to cut download + decode time.
- **Skip-if-present artifacts** so retries don't redo expensive stages.
- Target signal: time-to-first-section over total runtime; both tracked in App Insights.

### Latency budget (target: TTFS ≤ ~1–2 min, 1-hr captioned video)

The honest critical path for time-to-first-section is
`download proxy → transcript → index + segment the early part → first draft`. The two long
poles are **media download** and, only when captions are absent, **speech ASR**. This is why
captions-first (the transcript priority chain) is a *latency* lever, not just a quality one;
the ASR fallback fires the existing "speech-sourced, slower" `warning`.

Per-stage soft budgets (targets, tracked in App Insights; alert if p50 is breached):

| Stage | Target (1-hr captioned) | Notes |
| --- | --- | --- |
| `resolving` | < 5s | |
| `acquiring_media` (720p proxy) | < 30–60s | ⚠ main TTFS risk; bandwidth-bound |
| `transcribing` | < 10s (captions) / ~0.3–0.5× realtime (ASR) | ASR is the other long pole |
| `indexing_visual` (coarse) | parallel with transcript | early windows ready first |
| `segmenting` (fusion + 1 LLM call) | < 20s | |
| first-section draft | < 15s | |

→ ~2 min is realistic for a captioned video with a fast download. Driving TTFS below ~30s would
require **streaming segmentation of the early transcript** (segment before the whole video is
indexed); that is an explicit **post-v1 lever**, out of scope for v1.

---

## Cost model

Cost policy is **warn, never block** (`Decided defaults`). The app estimates cost up front,
shows it, always proceeds, and records actuals.

- `vtn_core` produces a `CostEstimate` at submit time from `duration × depth × configured
  per-unit rates`. **Rates live in config, never hardcoded prices.** Components:
  - **Transcript** — ≈ $0 when captions exist; per-audio-hour when Azure Speech ASR is used
    (the dominant *variable*).
  - **Frame OCR** — ∝ candidate frames *after* change-filtering, not all sampled frames.
  - **Embeddings** — semantic-shift windows; cents.
  - **LLM refinement** — one call.
  - **Per-section note generation** — the dominant LLM cost; scales with depth × section count.
  - **Storage / egress** — pennies, but accrues (see Data retention).
- The estimate is returned in the `202` submit response and as a `cost.estimate` SSE event; the
  UI shows an "Est. ~$X" banner. An optional configurable **soft ceiling** only recolors the
  banner to a warning — it never blocks.
- After the run, **actual** cost is computed from recorded usage (LLM token counts, audio
  minutes, OCR frame counts — captured as telemetry) and stored in `job_costs`; the UI shows
  actual-vs-estimate. Re-submit dedup (reusing proxy/transcript) is reflected in the estimate.

---

## Review mutation semantics

Principle: **user edits are never silently lost; a boundary change recomputes derived data but
flags it for review.**

- **Edit markdown** — debounced `PATCH` to `markdown_edited` on the current revision; never
  touches `markdown_draft`.
- **Regenerate** — creates a *new* `section_notes` revision with the new draft. If the prior
  revision had `markdown_edited` set, the UI warns first; the edited revision stays in history
  and is **one-click restorable** (restore appends a new revision copying that revision's
  content, keeping the table append-only).
- **Screenshots** — on *any* boundary change, screenshots **reassign by timestamp containment**
  to the resulting section(s); a manual screenshot outside all ranges attaches to the nearest.
- **Split / Merge — never auto-call the LLM** (keeps review snappy and cost predictable):
  - *Split at `at_sec`*: child 1 inherits the parent's current note as a fresh revision; child 2
    starts `pending`. Banner: "boundaries changed — regenerate to fit."
  - *Merge*: the result inherits the concatenation of inputs' current notes as a new `edited`
    revision. Same banner.
  - `order_index` is reindexed within a single transaction (preserving `UNIQUE(job_id,
    order_index)`).
- **Edit boundaries** (without split/merge) — adjusts the time range, reassigns screenshots by
  timestamp, leaves the note untouched, and shows the regenerate banner if the range changed
  materially.
- **Streaming-vs-editing concurrency** — SSE patches apply only to sections still in
  `{pending, drafting}`; once a section is `ready` or `edited`, late worker events for it are
  ignored. `PATCH` uses a revision / `updated_at` guard and returns `412` on a stale write.

---

## Deployment and CI/CD

### Infrastructure (Bicep modules under `infra/`, orchestrated by `azd`)

- `main.bicep` composes modules and outputs endpoints/connection info.
- Modules:
  - `containerapps-env.bicep` — ACA environment + Log Analytics workspace.
  - `acr.bicep` — Azure Container Registry.
  - `api.bicep` — API container app (ingress enabled, min/max replicas, scale on HTTP +
    concurrency).
  - `worker.bicep` — ACA **Job**, event-triggered by Service Bus queue depth (KEDA scaler).
  - `servicebus.bicep` — namespace, `jobs` queue, dead-letter config.
  - `storage.bicep` — Blob containers: `proxies`, `frames`, `screenshots`, `exports`.
  - `postgres.bicep` — PostgreSQL Flexible Server + database + firewall/VNet rules.
  - `keyvault.bicep` — secrets + access policies / RBAC.
  - `ai.bicep` — Azure AI Foundry / AI Services connections (Speech, Vision/Doc Intelligence).
  - `observability.bicep` — Application Insights.
- **Identity**: system-assigned managed identities for API and worker; RBAC grants to Blob,
  Service Bus, Key Vault, and AI resources. No connection strings with keys where managed
  identity is supported.

### Scaling rules

- API: scale 1→N on concurrent requests; min 1 for responsiveness.
- Worker Job: KEDA Service Bus scaler; scale to zero when the queue is empty, up to a small
  cap (e.g. 3) for one-at-a-time-per-user with headroom.

### CI/CD (GitHub Actions, OIDC to Azure)

1. Lint + unit tests (web, api, packages, worker).
2. Build API and worker container images.
3. Push to ACR.
4. `azd provision` / `azd deploy` (Bicep apply + container app revisions).
5. Smoke test against the deployed API (process a short sample video → assert
   `review_ready` + non-empty export).
- GitHub OIDC federation; **no long-lived Azure credentials** in GitHub secrets. Runtime
  secrets live in Key Vault and are referenced by managed identity.

### Database migrations

- **Alembic** manages the PostgreSQL schema; migrations are versioned in the repo.
- `alembic upgrade head` runs as a dedicated CD step (and in local startup). Segmentation
  weights and depth templates are seeded from config files, not migrations.

### Local development (offline, zero cloud spend)

- **`docker-compose`** brings up Postgres (with `pgcrypto` for `gen_random_uuid()` and native
  `LISTEN/NOTIFY`) and **Azurite** (Blob emulator).
- A **`fake` AI provider profile** returns deterministic fixture outputs for transcript, visual
  indexing, and LLM calls, so the *entire pipeline runs offline with no cloud spend*. The same
  fixtures back the integration tests.
- A **`QueueProvider` abstraction** lets local use an in-memory/SQLite-backed queue while Azure
  uses Service Bus — local needs no Service Bus emulator.
- `yt-dlp` / `ffmpeg` run locally as in production. Config is via `pydantic-settings` + `.env`
  with a `local` profile selecting the fakes and the local queue/storage.

---

## Security and configuration

- Access gate: a **single shared username/password** for the team. The password is stored as a
  **hash** in Key Vault (constant-time compare). `POST /login` issues a signed, httpOnly,
  Secure, `SameSite` **session cookie** with a sliding TTL; all `/api/v1` routes require it, and
  the SSE stream authenticates with the same cookie (no Authorization header needed). `/login`
  is rate-limited. Caveat: a shared login gives no per-person attribution or revocation —
  acceptable for a trusted small team and a single-tenant v1; it swaps cleanly to Entra ID
  behind the same cookie-session boundary later.
- Secrets (model endpoints/keys, DB credentials where MI isn't used) in Key Vault; injected as
  Container App secret references.
- All model ids/params externalized in `prompts.model_config` defaults + app config, not
  hard-coded (`Decided defaults`: Foundry-first, adapter-swappable).
- Blob containers are private; the browser reaches media/screenshots only through the
  authenticated API (range proxy / raw endpoints) or short-lived SAS URLs.
- Respect source terms of service for download; only public sessions.

---

## Reliability and error handling

- Jobs are **resumable by stage** (skip-if-present artifacts + recorded `stage` on failure).
- Failures persist `error_code`, `error_message`, and the failing `stage`; surfaced to the UI
  with an actionable message and retry.
- **No silent quality downgrade**: e.g. speech-sourced transcript or incomplete OCR is
  reported as a `warning` event/banner, not hidden.
- Service Bus dead-letters poison messages after capped retries; dead-lettered jobs show as
  `failed` with diagnostics.
- All stages emit structured logs + traces to Application Insights, correlated by `job_id`.

---

## Testing and evaluation

### Automated tests

- **Unit**: each resolver adapter; transcript provider priority; each `BoundaryDetector`;
  fusion scoring/clustering; screenshot dedup (pHash) + selection caps; markdown rendering;
  ZIP shape; export metadata.
- **Contract**: API endpoints (submit, sections CRUD, regenerate, capture, export) against a
  test DB; SSE replay via `Last-Event-ID`.
- **Integration**: worker stage runner with fakes for media/AI; resume-after-failure
  (skip-if-present) behavior.
- **E2E smoke**: process a short public sample video → assert `review_ready`, ≥1 section, and
  a non-empty export ZIP with valid relative image paths.

### AI quality evaluation

- Golden set of conference-style sample videos with reference notes/sections.
- Offline **eval harness** that runs segmentation + note generation and reports:
  section usefulness, boundary quality (vs reference), screenshot relevance, markdown
  correctness, faithfulness to evidence, and estimated user edit effort.
- The harness writes/reads `segmentation.weights` so heuristic weights are tuned from data,
  not guessed — directly supporting the "many speech variations" concern.

---

## Export format

ZIP layout:

```text
note.md
images/
  0001-intro.png
  0002-demo.png
  ...
metadata.json
```

- `note.md` references screenshots with relative paths, e.g.
  `![Demo architecture](images/0002-demo.png)`.
- `metadata.json` stores source URL, generation timestamp, note depth, transcript source,
  per-section timestamps, and per-screenshot timestamps for audit/re-import.

---

## Open questions (low-risk, defer to implementation)

- Exact Foundry model deployments (ids/quota/region) — externalized in config.
- Component library choice for the Next.js UI (must support accessible forms, cards, editor,
  scrubber).
- Whether to introduce Azure Web PubSub instead of PostgreSQL `LISTEN/NOTIFY` for SSE fan-out
  if event volume grows.
- Whether Azure AI Video Indexer is added as an optional visual adapter in v1 or after the
  baseline local index is validated.
- Whether Google/Gemini multimodal is benchmarked in v1 or post-v1 (adapter boundary exists
  either way).
