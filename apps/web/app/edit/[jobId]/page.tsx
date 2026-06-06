"use client";

import { useEffect, useState } from "react";

import {
  ProgressiveTimeline,
  TimelineState,
} from "../../../components/timeline/progressive-timeline";
import { JobEvent, connectJobEvents } from "../../../lib/sse";

const INITIAL_TIMELINE: TimelineState = {
  clipsReady: false,
  readyClips: [],
  reviewReady: false,
  screenshotsReady: false,
  transcriptReady: false,
  videoReady: false,
};

export default function EditPage({ params }: { params: { jobId: string } }) {
  const [timeline, setTimeline] = useState<TimelineState>(INITIAL_TIMELINE);

  useEffect(() => {
    return connectJobEvents(params.jobId, (event) => {
      setTimeline((current) => reduceTimeline(current, event));
    });
  }, [params.jobId]);

  return (
    <main className="edit-shell">
      <header className="edit-header">
        <h1>Edit note</h1>
        <span>{timeline.reviewReady ? "Review ready" : "Preparing"}</span>
      </header>

      <ProgressiveTimeline state={timeline} />

      <section className="tool-row" aria-label="Edit tools">
        <button disabled={!timeline.reviewReady} type="button">
          Split
        </button>
        <button disabled={!timeline.reviewReady} type="button">
          Merge
        </button>
        <button disabled={!timeline.reviewReady} type="button">
          Set scene
        </button>
        <button disabled={!timeline.reviewReady} type="button">
          Edit clip
        </button>
      </section>
    </main>
  );
}

function reduceTimeline(current: TimelineState, event: JobEvent): TimelineState {
  if (event.type === "done") {
    return { ...current, reviewReady: true };
  }
  if (event.type === "clip.ready") {
    return {
      ...current,
      readyClips: [...new Set([...current.readyClips, event.payload.order_index])].sort(
        (left, right) => left - right,
      ),
    };
  }
  if (event.type !== "stage") {
    return current;
  }

  switch (event.payload.stage) {
    case "acquiring_media":
      return { ...current, videoReady: true };
    case "transcribe":
      return { ...current, transcriptReady: true };
    case "index visual":
      return { ...current, screenshotsReady: true };
    case "segmenting":
      return { ...current, clipsReady: true };
    case "drafting":
      return current;
    default:
      return current;
  }
}
