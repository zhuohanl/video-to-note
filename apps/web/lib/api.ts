export type ApiErrorEnvelope = {
  error?: {
    code?: string;
    message?: string;
  };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export type PromptDepth = "thorough" | "balanced" | "brief" | "custom";

export type ExampleNote = {
  filename: string;
  content: string;
  save_as_default: boolean;
};

export type CostEstimate = {
  usd?: string;
  breakdown?: Record<string, unknown>;
};

export type CreateJobInput = {
  url: string;
  depth: PromptDepth;
  custom_prompt: string | null;
  examples: ExampleNote[];
  use_saved_style: boolean;
};

export type CreateJobResponse = {
  job_id: string;
  cost_estimate: CostEstimate;
};

export type ClipView = {
  id: string;
  order_index: number;
  start_sec: string;
  end_sec: string;
  title: string | null;
  summary: string | null;
  scene_caption?: string | null;
  scene_at_sec: string | null;
  scene_url: string | null;
  scene_source: string;
  needs_regen: boolean;
  etag: string;
};

export type ClipsView = {
  clips: ClipView[];
  collection_etag: string;
};

export type NoteView = {
  markdown: string;
  include_summary: boolean;
  include_transcript: boolean;
  is_polished: boolean;
  clips_dirty: boolean;
  etag: string;
};

export type VersionView = {
  seq: number;
  label: string | null;
  kind: string;
  baseline?: boolean;
};

export async function login(username: string, password: string): Promise<void> {
  const response = await fetch("/login", {
    body: JSON.stringify({ username, password }),
    credentials: "include",
    headers: { "content-type": "application/json" },
    method: "POST",
  });

  if (!response.ok) {
    const envelope = await readEnvelope(response);
    throw new ApiError(
      response.status,
      envelope.error?.code ?? "request_failed",
      envelope.error?.message ?? "Sign in failed",
    );
  }
}

export async function createJob(input: CreateJobInput): Promise<CreateJobResponse> {
  const response = await fetch("/jobs", {
    body: JSON.stringify(input),
    credentials: "include",
    headers: { "content-type": "application/json" },
    method: "POST",
  });

  if (!response.ok) {
    const envelope = await readEnvelope(response);
    throw new ApiError(
      response.status,
      envelope.error?.code ?? "request_failed",
      envelope.error?.message ?? "Could not create note",
    );
  }

  return (await response.json()) as CreateJobResponse;
}

export async function getClips(jobId: string): Promise<ClipsView> {
  return requestJson<ClipsView>(`/jobs/${jobId}/clips`);
}

export async function getNote(jobId: string): Promise<NoteView> {
  return requestJson<NoteView>(`/jobs/${jobId}/note`);
}

export async function patchClip(
  clipId: string,
  etag: string,
  body: { title?: string; summary?: string | null; scene_caption?: string | null },
  ack = false,
): Promise<ClipView> {
  return requestJson<ClipView>(`/clips/${clipId}${ack ? "?ack=1" : ""}`, {
    body: JSON.stringify(body),
    headers: { "content-type": "application/json", "if-match": etag },
    method: "PATCH",
  });
}

export async function splitClip(
  clipId: string,
  collectionEtag: string,
  atSec: string,
  ack = false,
): Promise<ClipsView> {
  return requestJson<ClipsView>(`/clips/${clipId}/split${ack ? "?ack=1" : ""}`, {
    body: JSON.stringify({ at_sec: atSec }),
    headers: { "content-type": "application/json", "if-match": collectionEtag },
    method: "POST",
  });
}

export async function mergeClips(clipIds: string[], collectionEtag: string): Promise<ClipsView> {
  return requestJson<ClipsView>("/clips/merge", {
    body: JSON.stringify({ clip_ids: clipIds }),
    headers: { "content-type": "application/json", "if-match": collectionEtag },
    method: "POST",
  });
}

export async function regenerateClip(clipId: string, etag: string, ack = false): Promise<ClipView> {
  return requestJson<ClipView>(`/clips/${clipId}/regenerate${ack ? "?ack=1" : ""}`, {
    headers: { "if-match": etag },
    method: "POST",
  });
}

export async function setScene(clipId: string, etag: string, atSec: string): Promise<object> {
  return requestJson<object>(`/clips/${clipId}/scene`, {
    body: JSON.stringify({ at_sec: atSec }),
    headers: { "content-type": "application/json", "if-match": etag },
    method: "POST",
  });
}

export async function putNote(jobId: string, etag: string, markdown: string): Promise<NoteView> {
  return requestJson<NoteView>(`/jobs/${jobId}/note`, {
    body: JSON.stringify({ markdown }),
    headers: { "content-type": "application/json", "if-match": etag },
    method: "PUT",
  });
}

export async function patchNote(
  jobId: string,
  etag: string,
  body: { include_summary?: boolean; include_transcript?: boolean },
): Promise<NoteView> {
  return requestJson<NoteView>(`/jobs/${jobId}/note`, {
    body: JSON.stringify(body),
    headers: { "content-type": "application/json", "if-match": etag },
    method: "PATCH",
  });
}

export async function rebuildNote(jobId: string, etag: string): Promise<NoteView> {
  return requestJson<NoteView>(`/jobs/${jobId}/note/rebuild`, {
    headers: { "if-match": etag },
    method: "POST",
  });
}

export async function keepNote(jobId: string, etag: string): Promise<NoteView> {
  return requestJson<NoteView>(`/jobs/${jobId}/note/keep`, {
    headers: { "if-match": etag },
    method: "POST",
  });
}

export async function listVersions(jobId: string): Promise<VersionView[]> {
  const response = await requestJson<{ versions: VersionView[] }>(`/jobs/${jobId}/versions`);
  return response.versions;
}

export async function saveVersion(
  jobId: string,
  noteEtag: string,
  clipsEtag: string,
  label: string | null = null,
): Promise<VersionView> {
  return requestJson<VersionView>(`/jobs/${jobId}/versions`, {
    body: JSON.stringify({ label }),
    headers: { "content-type": "application/json", "if-match": `${noteEtag}, ${clipsEtag}` },
    method: "POST",
  });
}

export async function restoreVersion(
  jobId: string,
  seq: number,
  noteEtag: string,
  clipsEtag: string,
): Promise<object> {
  return requestJson<object>(`/jobs/${jobId}/versions/${seq}/restore`, {
    headers: { "if-match": `${noteEtag}, ${clipsEtag}` },
    method: "POST",
  });
}

async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(url, { credentials: "include", ...init });
  if (!response.ok) {
    const envelope = await readEnvelope(response);
    throw new ApiError(
      response.status,
      envelope.error?.code ?? "request_failed",
      envelope.error?.message ?? "Request failed",
    );
  }
  return (await response.json()) as T;
}

async function readEnvelope(response: Response): Promise<ApiErrorEnvelope> {
  try {
    return (await response.json()) as ApiErrorEnvelope;
  } catch {
    return {};
  }
}
