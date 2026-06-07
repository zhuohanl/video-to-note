import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EditClient } from "../app/edit/[jobId]/client";

class MockEventSource {
  static instances: MockEventSource[] = [];
  readonly listeners = new Map<string, ((event: MessageEvent) => void)[]>();

  constructor(readonly url: string) {
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close() {}

  emit(type: string, data: object, lastEventId: string) {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(new MessageEvent(type, { data: JSON.stringify(data), lastEventId }));
    }
  }
}

const clipA = {
  id: "clip-a",
  order_index: 0,
  start_sec: "0.000",
  end_sec: "5.000",
  title: "Intro",
  summary: "Original summary",
  scene_at_sec: "1.000",
  scene_url: "local://frames/a.png",
  scene_source: "auto",
  needs_regen: true,
  etag: '"clip-a-v1"',
};

const clipB = {
  ...clipA,
  id: "clip-b",
  order_index: 1,
  title: "Deep Dive",
  needs_regen: false,
  etag: '"clip-b-v1"',
};

function json(body: object, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

function clipsView(clips = [clipA, clipB], collection = '"clips-v1"') {
  return { clips, collection_etag: collection };
}

function noteView(isPolished = true) {
  return {
    markdown: "# Note",
    include_summary: true,
    include_transcript: false,
    is_polished: isPolished,
    clips_dirty: false,
    etag: '"note-v1"',
  };
}

describe("edit tools", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows needs_ack modal and retries the mutation with ack=1", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(json(clipsView()))
      .mockResolvedValueOnce(json(noteView(true)))
      .mockResolvedValueOnce(json({ error: { code: "needs_ack", message: "Needs ack" } }, 409))
      .mockResolvedValueOnce(json({ ...clipA, summary: "Edited summary", etag: '"clip-a-v2"' }));

    renderEditPage();
    await screen.findByDisplayValue("Original summary");
    expect(screen.getByText("Note will refresh")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Summary"), { target: { value: "Edited summary" } });
    fireEvent.click(screen.getByRole("button", { name: "Save clip" }));
    expect(await screen.findByRole("dialog")).toHaveTextContent("This clip change will refresh");

    fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenLastCalledWith("/clips/clip-a?ack=1", {
        body: JSON.stringify({ summary: "Edited summary", title: "Intro" }),
        credentials: "include",
        headers: { "content-type": "application/json", "if-match": '"clip-a-v1"' },
        method: "PATCH",
      }),
    );
    expect(await screen.findByDisplayValue("Edited summary")).toBeInTheDocument();
  });

  it("does not auto-retry 412 writes and reapplies only after user confirmation", async () => {
    const refreshed = {
      ...clipA,
      summary: "Server summary",
      etag: '"clip-a-v2"',
    };
    vi.mocked(fetch)
      .mockResolvedValueOnce(json(clipsView()))
      .mockResolvedValueOnce(json(noteView(false)))
      .mockResolvedValueOnce(json({ error: { code: "stale_write", message: "Stale" } }, 412))
      .mockResolvedValueOnce(json(clipsView([refreshed, clipB], '"clips-v2"')))
      .mockResolvedValueOnce(json(noteView(false)))
      .mockResolvedValueOnce(json({ ...refreshed, summary: "Local edit", etag: '"clip-a-v3"' }));

    renderEditPage();
    await screen.findByDisplayValue("Original summary");
    fireEvent.change(screen.getByLabelText("Summary"), { target: { value: "Local edit" } });
    fireEvent.click(screen.getByRole("button", { name: "Save clip" }));

    expect(await screen.findByText("Changed elsewhere - review and reapply")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(5);
    expect(await screen.findByDisplayValue("Server summary")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Reapply edit" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenLastCalledWith("/clips/clip-a", {
        body: JSON.stringify({ summary: "Local edit", title: "Intro" }),
        credentials: "include",
        headers: { "content-type": "application/json", "if-match": '"clip-a-v2"' },
        method: "PATCH",
      }),
    );
  });

  it("restores AI summary, regenerates, and calls structural tools with ETags", async () => {
    const restored = { ...clipA, summary: "AI summary", etag: '"clip-a-v2"' };
    const regenerated = { ...restored, needs_regen: false, etag: '"clip-a-v3"' };
    vi.mocked(fetch)
      .mockResolvedValueOnce(json(clipsView()))
      .mockResolvedValueOnce(json(noteView(false)))
      .mockResolvedValueOnce(json(restored))
      .mockResolvedValueOnce(json(regenerated))
      .mockResolvedValueOnce(json(clipsView([regenerated, clipB], '"clips-v2"')))
      .mockResolvedValueOnce(json(clipsView([regenerated], '"clips-v3"')))
      .mockResolvedValueOnce(json({ scene_at_sec: "2.000", etag: '"clip-a-v4"' }));

    renderEditPage();
    await screen.findByText("Needs regeneration");

    fireEvent.click(screen.getByRole("button", { name: "Restore AI summary" }));
    expect(await screen.findByDisplayValue("AI summary")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Regenerate" }));
    await waitFor(() => expect(screen.queryByText("Needs regeneration")).not.toBeInTheDocument());

    unlockTools();
    fireEvent.click(screen.getByRole("button", { name: "Split" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/clips/clip-a/split", {
        body: JSON.stringify({ at_sec: "2.500" }),
        credentials: "include",
        headers: { "content-type": "application/json", "if-match": '"clips-v1"' },
        method: "POST",
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Merge" }));
    fireEvent.click(screen.getByRole("button", { name: "Set scene" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenLastCalledWith("/clips/clip-a/scene", {
        body: JSON.stringify({ at_sec: "2.000" }),
        credentials: "include",
        headers: { "content-type": "application/json", "if-match": '"clip-a-v3"' },
        method: "POST",
      }),
    );
    expect(fetch).toHaveBeenCalledWith("/clips/merge", {
      body: JSON.stringify({ clip_ids: ["clip-a", "clip-b"] }),
      credentials: "include",
      headers: { "content-type": "application/json", "if-match": '"clips-v2"' },
      method: "POST",
    });
  });
});

function renderEditPage() {
  render(<EditClient jobId="job-1" />);
}

function unlockTools() {
  act(() => MockEventSource.instances[0].emit("done", {}, "9"));
}
