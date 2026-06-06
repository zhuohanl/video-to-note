import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EditClient } from "../app/edit/[jobId]/client";

type Listener = (event: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];
  readonly listeners = new Map<string, Listener[]>();
  closed = false;

  constructor(readonly url: string) {
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close() {
    this.closed = true;
  }

  emit(type: string, data: object, lastEventId: string) {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(new MessageEvent(type, { data: JSON.stringify(data), lastEventId }));
    }
  }

  fail() {
    for (const listener of this.listeners.get("error") ?? []) {
      listener(new MessageEvent("error"));
    }
  }
}

describe("edit SSE", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("fills lanes from SSE events and unlocks tools only when done", () => {
    renderEditPage();

    expect(screen.getByText("Preparing")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Split" })).toBeDisabled();
    expect(screen.getByText("Preparing video")).toBeInTheDocument();
    expect(screen.getByText("Transcript rows blank")).toBeInTheDocument();
    expect(screen.getByText("Placeholder thumbnails")).toBeInTheDocument();
    expect(screen.getByText("Timeline empty")).toBeInTheDocument();
    expect(screen.getByText("Summary skeletons pending")).toBeInTheDocument();

    const source = MockEventSource.instances[0];
    act(() => source.emit("stage", { stage: "acquiring_media" }, "1"));
    expect(screen.getByText("Video ready")).toBeInTheDocument();

    act(() => source.emit("stage", { stage: "transcribe" }, "2"));
    expect(screen.getByText("Transcript ready")).toBeInTheDocument();

    act(() => source.emit("stage", { stage: "index visual" }, "3"));
    expect(screen.getByText("Screenshots ready")).toBeInTheDocument();

    act(() => source.emit("stage", { stage: "segmenting" }, "4"));
    expect(screen.getByText("Clip boundaries ready")).toBeInTheDocument();

    act(() => source.emit("clip.ready", { clip_id: "clip-1", order_index: 0 }, "5"));
    expect(screen.getByText("Clip 1 summary ready")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Merge" })).toBeDisabled();

    act(() => source.emit("done", {}, "6"));
    expect(screen.getByText("Review ready")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Split" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Merge" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Set scene" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Edit clip" })).toBeEnabled();
  });

  it("reconnects with the last event id", () => {
    renderEditPage();
    expect(screen.getByText("Preparing")).toBeInTheDocument();

    const source = MockEventSource.instances[0];
    act(() => source.emit("stage", { stage: "transcribe" }, "7"));
    act(() => source.fail());
    act(() => vi.runOnlyPendingTimers());

    expect(source.closed).toBe(true);
    expect(MockEventSource.instances).toHaveLength(2);
    expect(MockEventSource.instances[1].url).toBe("/jobs/job-1/events?last_event_id=7");
  });

  it("keeps tools gated after project data loads until the done event arrives", async () => {
    vi.useRealTimers();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          json({
            clips: [
              {
                id: "clip-a",
                order_index: 0,
                start_sec: "0.000",
                end_sec: "5.000",
                title: "Intro",
                summary: "Summary",
                scene_at_sec: "1.000",
                scene_url: null,
                scene_source: "auto",
                needs_regen: false,
                etag: '"clip-v1"',
              },
            ],
            collection_etag: '"clips-v1"',
          }),
        )
        .mockResolvedValueOnce(
          json({
            markdown: "## 1. Intro\n\nSummary",
            include_summary: true,
            include_transcript: false,
            is_polished: false,
            clips_dirty: false,
            etag: '"note-v1"',
          }),
        ),
    );

    renderEditPage();

    await waitFor(() => expect(screen.getByLabelText("Summary")).toHaveValue("Summary"));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    expect(screen.getByText("Preparing")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Split" })).toBeDisabled();
  });
});

function renderEditPage() {
  render(<EditClient jobId="job-1" />);
}

function json(body: object) {
  return new Response(JSON.stringify(body), { status: 200 });
}
