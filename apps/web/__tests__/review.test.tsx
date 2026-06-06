import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ReviewClient } from "../app/review/[jobId]/client";

const note = {
  markdown: "## 1. Intro\n\nOriginal prose",
  include_summary: true,
  include_transcript: false,
  is_polished: false,
  clips_dirty: true,
  etag: '"note-v1"',
};

const clip = {
  id: "clip-a",
  order_index: 0,
  start_sec: "0.000",
  end_sec: "5.000",
  title: "Intro",
  summary: "Original prose",
  scene_caption: "Original caption",
  scene_at_sec: "1.000",
  scene_url: "local://frames/a.png",
  scene_source: "auto",
  needs_regen: false,
  etag: '"clip-v1"',
};

function json(body: object, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

function clipsView(etag = '"clips-v1"') {
  return { clips: [clip], collection_etag: etag };
}

describe("review page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("debounces autosave with note ETag and edits captions through clip PATCH", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(json(note))
      .mockResolvedValueOnce(json(clipsView()))
      .mockResolvedValueOnce(json({ versions: [] }))
      .mockResolvedValueOnce(json({ ...note, markdown: "Edited prose", etag: '"note-v2"' }))
      .mockResolvedValueOnce(json({ ...clip, scene_caption: "Edited caption", etag: '"clip-v2"' }));

    renderReviewPage();
    const editor = await screen.findByLabelText("Markdown editor");
    fireEvent.change(editor, { target: { value: "Edited prose" } });
    expect(fetch).toHaveBeenCalledTimes(3);

    await new Promise((resolve) => setTimeout(resolve, 550));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/jobs/job-1/note", {
        body: JSON.stringify({ markdown: "Edited prose" }),
        credentials: "include",
        headers: { "content-type": "application/json", "if-match": '"note-v1"' },
        method: "PUT",
      }),
    );

    fireEvent.change(screen.getByLabelText("Scene caption"), {
      target: { value: "Edited caption" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save caption" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenLastCalledWith("/clips/clip-a", {
        body: JSON.stringify({ scene_caption: "Edited caption" }),
        credentials: "include",
        headers: { "content-type": "application/json", "if-match": '"clip-v1"' },
        method: "PATCH",
      }),
    );
  });

  it("persists content booleans only and keeps prose editable in transcript-only mode", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(json(note))
      .mockResolvedValueOnce(json(clipsView()))
      .mockResolvedValueOnce(json({ versions: [] }))
      .mockResolvedValueOnce(json({ ...note, include_transcript: true, etag: '"note-v2"' }))
      .mockResolvedValueOnce(
        json({
          ...note,
          include_summary: false,
          include_transcript: true,
          etag: '"note-v3"',
        }),
      );

    renderReviewPage();
    await screen.findByLabelText("Markdown editor");

    fireEvent.click(screen.getByLabelText("Transcript"));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/jobs/job-1/note", {
        body: JSON.stringify({ include_transcript: true }),
        credentials: "include",
        headers: { "content-type": "application/json", "if-match": '"note-v1"' },
        method: "PATCH",
      }),
    );

    fireEvent.click(screen.getByLabelText("Summary"));
    expect(await screen.findByText("Summary excluded from output")).toBeInTheDocument();
    expect(screen.getByLabelText("Markdown editor")).toHaveValue(note.markdown);
    expect(screen.queryByText("Original prose", { selector: ".preview-body" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Transcript")).toBeDisabled();
  });

  it("shows rebuild banner and restores versions with both ETags", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(json(note))
      .mockResolvedValueOnce(json(clipsView()))
      .mockResolvedValueOnce(json({ versions: [{ seq: 2, label: "Checkpoint", kind: "manual" }] }))
      .mockResolvedValueOnce(json({ ...note, clips_dirty: false, etag: '"note-v2"' }))
      .mockResolvedValueOnce(json({ status: "restored" }));

    renderReviewPage();
    expect(await screen.findByText("Clips changed since this note was polished")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Rebuild" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith("/jobs/job-1/note/rebuild", {
        credentials: "include",
        headers: { "if-match": '"note-v1"' },
        method: "POST",
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Restore v2" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenLastCalledWith("/jobs/job-1/versions/2/restore", {
        credentials: "include",
        headers: { "if-match": '"note-v2", "clips-v1"' },
        method: "POST",
      }),
    );
  });
});

function renderReviewPage() {
  render(<ReviewClient jobId="job-1" />);
}
