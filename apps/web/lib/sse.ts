export type JobEvent =
  | { type: "stage"; id: number; payload: { stage: string } }
  | { type: "clip.ready"; id: number; payload: { clip_id: string; order_index: number } }
  | { type: "done"; id: number; payload: Record<string, never> }
  | { type: "warning"; id: number; payload: { code: string; message: string } }
  | { type: "error"; id: number; payload: { code: string; message: string; stage: string } };

export type JobEventHandler = (event: JobEvent) => void;

const EVENT_TYPES = ["stage", "clip.ready", "done", "warning", "error"] as const;
const RECONNECT_MS = 25;

export function connectJobEvents(jobId: string, onEvent: JobEventHandler) {
  let source: EventSource | null = null;
  let lastEventId = 0;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let closed = false;

  function open() {
    const query = lastEventId > 0 ? `?last_event_id=${lastEventId}` : "";
    source = new EventSource(`/jobs/${jobId}/events${query}`);
    for (const type of EVENT_TYPES) {
      source.addEventListener(type, (raw) => {
        const event = raw as MessageEvent<string>;
        const numericId = Number(event.lastEventId);
        if (Number.isFinite(numericId) && numericId > 0) {
          lastEventId = numericId;
        }
        onEvent({ type, id: lastEventId, payload: JSON.parse(event.data || "{}") } as JobEvent);
      });
    }
    source.addEventListener("error", () => {
      if (closed) {
        return;
      }
      source?.close();
      reconnectTimer = setTimeout(open, RECONNECT_MS);
    });
  }

  open();

  return () => {
    closed = true;
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
    }
    source?.close();
  };
}
