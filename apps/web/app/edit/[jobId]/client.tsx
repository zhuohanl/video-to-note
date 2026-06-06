"use client";

import { useEffect, useState } from "react";

import {
  ProgressiveTimeline,
  TimelineState,
} from "../../../components/timeline/progressive-timeline";
import {
  ApiError,
  ClipView,
  ClipsView,
  NoteView,
  getClips,
  getNote,
  mergeClips,
  patchClip,
  regenerateClip,
  setScene,
  splitClip,
} from "../../../lib/api";
import { JobEvent, connectJobEvents } from "../../../lib/sse";

const INITIAL_TIMELINE: TimelineState = {
  clipsReady: false,
  readyClips: [],
  reviewReady: false,
  screenshotsReady: false,
  transcriptReady: false,
  videoReady: false,
};

export function EditClient({ jobId }: { jobId: string }) {
  const [timeline, setTimeline] = useState<TimelineState>(INITIAL_TIMELINE);
  const [clipsView, setClipsView] = useState<ClipsView | null>(null);
  const [note, setNote] = useState<NoteView | null>(null);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [ackAction, setAckAction] = useState<(() => Promise<void>) | null>(null);
  const [staleAction, setStaleAction] = useState<(() => Promise<void>) | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    return connectJobEvents(jobId, (event) => {
      setTimeline((current) => reduceTimeline(current, event));
    });
  }, [jobId]);

  useEffect(() => {
    void refreshProject(jobId);
  }, [jobId]);

  const selectedClip = clipsView?.clips.find((clip) => clip.id === selectedClipId) ?? null;

  useEffect(() => {
    if (!selectedClip) {
      return;
    }
    setTitle(selectedClip.title ?? "");
    setSummary(selectedClip.summary ?? "");
  }, [selectedClip]);

  async function refreshProject(jobId: string) {
    try {
      const [nextClips, nextNote] = await Promise.all([getClips(jobId), getNote(jobId)]);
      setClipsView(nextClips);
      setNote(nextNote);
      setSelectedClipId((current) => current ?? nextClips.clips[0]?.id ?? null);
      setTimeline((current) => ({ ...current, reviewReady: true }));
    } catch {
      return;
    }
  }

  function updateClip(updated: ClipView) {
    setClipsView((current) =>
      current
        ? {
            ...current,
            clips: current.clips.map((clip) => (clip.id === updated.id ? updated : clip)),
          }
        : current,
    );
  }

  async function runClipMutation(
    operation: (ack: boolean) => Promise<ClipView>,
    reapply?: (clip: ClipView) => Promise<ClipView>,
  ) {
    try {
      updateClip(await operation(false));
      setNotice("");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409 && caught.code === "needs_ack") {
        setAckAction(() => async () => {
          updateClip(await operation(true));
          setAckAction(null);
        });
        return;
      }
      if (caught instanceof ApiError && caught.status === 412) {
        const [nextClips, nextNote] = await Promise.all([getClips(jobId), getNote(jobId)]);
        setClipsView(nextClips);
        setNote(nextNote);
        const refreshed = nextClips.clips.find((clip) => clip.id === selectedClipId);
        setNotice("Changed elsewhere - review and reapply");
        if (reapply && refreshed) {
          setStaleAction(() => async () => {
            updateClip(await reapply(refreshed));
            setStaleAction(null);
            setNotice("");
          });
        }
      }
    }
  }

  async function saveClip() {
    if (!selectedClip) {
      return;
    }
    await runClipMutation(
      (ack) => patchClip(selectedClip.id, selectedClip.etag, { summary, title }, ack),
      (clip) => patchClip(clip.id, clip.etag, { summary, title }),
    );
  }

  async function restoreAiSummary() {
    if (!selectedClip) {
      return;
    }
    await runClipMutation((ack) => patchClip(selectedClip.id, selectedClip.etag, { summary: null }, ack));
  }

  async function regenerateSelected() {
    if (!selectedClip) {
      return;
    }
    await runClipMutation((ack) => regenerateClip(selectedClip.id, selectedClip.etag, ack));
  }

  async function splitSelected() {
    if (!selectedClip || !clipsView) {
      return;
    }
    const atSec = midpoint(selectedClip.start_sec, selectedClip.end_sec);
    const next = await splitClip(selectedClip.id, clipsView.collection_etag, atSec);
    setClipsView(next);
  }

  async function mergeFirstPair() {
    if (!clipsView || clipsView.clips.length < 2) {
      return;
    }
    const next = await mergeClips(
      [clipsView.clips[0].id, clipsView.clips[1].id],
      clipsView.collection_etag,
    );
    setClipsView(next);
  }

  async function setSelectedScene() {
    if (!selectedClip) {
      return;
    }
    await setScene(selectedClip.id, selectedClip.etag, "2.000");
  }

  return (
    <main className="edit-shell">
      <header className="edit-header">
        <h1>Edit note</h1>
        <span>{timeline.reviewReady ? "Review ready" : "Preparing"}</span>
      </header>

      <ProgressiveTimeline state={timeline} />

      <section className="tool-row" aria-label="Edit tools">
        <button disabled={!timeline.reviewReady} onClick={splitSelected} type="button">
          Split
        </button>
        <button disabled={!timeline.reviewReady} onClick={mergeFirstPair} type="button">
          Merge
        </button>
        <button disabled={!timeline.reviewReady} onClick={setSelectedScene} type="button">
          Set scene
        </button>
        <button disabled={!timeline.reviewReady} type="button">
          Edit clip
        </button>
      </section>

      {selectedClip ? (
        <section className="inspector-panel" aria-label="Clip inspector">
          <header>
            <h2>{selectedClip.title}</h2>
            {note?.is_polished ? <span>Note will refresh</span> : null}
            {selectedClip.needs_regen ? <span>Needs regeneration</span> : null}
          </header>
          <label>
            Title
            <input onChange={(event) => setTitle(event.target.value)} value={title} />
          </label>
          <label>
            Summary
            <textarea onChange={(event) => setSummary(event.target.value)} value={summary} />
          </label>
          {notice ? <p role="status">{notice}</p> : null}
          <div className="inspector-actions">
            <button onClick={saveClip} type="button">
              Save clip
            </button>
            <button onClick={restoreAiSummary} type="button">
              Restore AI summary
            </button>
            {selectedClip.needs_regen ? (
              <button onClick={regenerateSelected} type="button">
                Regenerate
              </button>
            ) : null}
            {staleAction ? (
              <button onClick={() => void staleAction()} type="button">
                Reapply edit
              </button>
            ) : null}
          </div>
        </section>
      ) : null}

      {ackAction ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-panel">
            <p>This clip change will refresh the note.</p>
            <button onClick={() => void ackAction()} type="button">
              Keep editing
            </button>
            <button onClick={() => setAckAction(null)} type="button">
              Cancel
            </button>
          </div>
        </div>
      ) : null}
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

function midpoint(start: string, end: string): string {
  return ((Number(start) + Number(end)) / 2).toFixed(3);
}
