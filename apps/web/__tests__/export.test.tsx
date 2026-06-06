import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ExportPage from "../app/export/[jobId]/page";

function json(body: object, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

describe("export page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("open", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders counts and follows the export download URL", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        json({
          clips: [
            { id: "clip-a", scene_url: "local://frames/a.png" },
            { id: "clip-b", scene_url: "local://frames/b.png" },
          ],
          collection_etag: '"clips"',
        }),
      )
      .mockResolvedValueOnce(
        json({
          markdown: "## One\n\nBody\n\n## Two\n\nBody",
          include_summary: true,
          include_transcript: false,
          is_polished: false,
          clips_dirty: false,
          etag: '"note"',
        }),
      )
      .mockResolvedValueOnce(json({ download_url: "local://exports/job-1.zip" }));

    render(<ExportPage params={{ jobId: "job-1" }} />);

    expect(await screen.findByText("2 sections")).toBeInTheDocument();
    expect(screen.getByText("2 screenshots")).toBeInTheDocument();
    expect(screen.getByText("note.md")).toBeInTheDocument();
    expect(screen.getByText("images/")).toBeInTheDocument();
    expect(screen.getByText("metadata.json")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Download ZIP" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenLastCalledWith("/jobs/job-1/export", {
        credentials: "include",
        method: "POST",
      }),
    );
    expect(open).toHaveBeenCalledWith("local://exports/job-1.zip", "_self");
  });
});
