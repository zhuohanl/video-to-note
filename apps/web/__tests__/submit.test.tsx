import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SubmitPage from "../app/submit/page";
import { MAX_EXAMPLE_BYTES } from "../app/submit/constants";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

describe("submit", () => {
  beforeEach(() => {
    push.mockReset();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("reveals the custom prompt field for custom depth", () => {
    render(<SubmitPage />);

    expect(screen.queryByLabelText("Custom prompt")).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("I'll prompt it"));

    expect(screen.getByLabelText("Custom prompt")).toBeInTheDocument();
  });

  it("rejects non-markdown and oversized examples client-side", () => {
    render(<SubmitPage />);
    const input = screen.getByLabelText("Add Markdown examples");

    fireEvent.change(input, {
      target: { files: [new File(["text"], "notes.txt", { type: "text/plain" })] },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Only .md files are supported.");

    fireEvent.change(input, {
      target: { files: [new File(["x".repeat(MAX_EXAMPLE_BYTES + 1)], "huge.md")] },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Example file is too large.");
  });

  it("submits a job, renders the estimate, and navigates to edit", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          job_id: "job-123",
          cost_estimate: {
            usd: "0.1234",
            breakdown: { expected_clips: 2, llm_calls: 4, ocr_frames: 10 },
          },
        }),
        { status: 202 },
      ),
    );
    render(<SubmitPage />);

    fireEvent.change(screen.getByLabelText("Video URL"), {
      target: { value: "https://www.youtube.com/watch?v=demo" },
    });
    fireEvent.click(screen.getByLabelText("Thorough"));
    fireEvent.click(screen.getByLabelText("Use saved style"));
    fireEvent.change(screen.getByLabelText("Add Markdown examples"), {
      target: { files: [new File(["# Example"], "example.md", { type: "text/markdown" })] },
    });
    await screen.findByText("1 example ready");
    fireEvent.click(screen.getByLabelText("Save as my default style"));
    fireEvent.click(screen.getByRole("button", { name: "Create note" }));

    await screen.findByText("$0.1234");
    await waitFor(() => expect(push).toHaveBeenCalledWith("/edit/job-123"));
    expect(fetch).toHaveBeenCalledWith("/jobs", {
      body: JSON.stringify({
        custom_prompt: null,
        depth: "thorough",
        examples: [{ content: "# Example", filename: "example.md", save_as_default: true }],
        url: "https://www.youtube.com/watch?v=demo",
        use_saved_style: true,
      }),
      credentials: "include",
      headers: { "content-type": "application/json" },
      method: "POST",
    });
  });
});
