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

async function readEnvelope(response: Response): Promise<ApiErrorEnvelope> {
  try {
    return (await response.json()) as ApiErrorEnvelope;
  } catch {
    return {};
  }
}
