"use client";

import { useEffect, useMemo, useState } from "react";

import { ContentSelector } from "../../../components/content-selector/content-selector";
import { DocEditor } from "../../../components/doc-editor/doc-editor";
import { VersionHistory } from "../../../components/version-history/version-history";
import {
  ClipView,
  ClipsView,
  NoteView,
  VersionView,
  getClips,
  getNote,
  keepNote,
  listVersions,
  patchClip,
  patchNote,
  putNote,
  rebuildNote,
  restoreVersion,
  saveVersion,
} from "../../../lib/api";

const AUTOSAVE_MS = 500;

export default function ReviewPage({ params }: { params: { jobId: string } }) {
  const [note, setNote] = useState<NoteView | null>(null);
  const [clipsView, setClipsView] = useState<ClipsView | null>(null);
  const [versions, setVersions] = useState<VersionView[]>([]);
  const [markdown, setMarkdown] = useState("");
  const [caption, setCaption] = useState("");
  const [error, setError] = useState("");

  const clip = clipsView?.clips[0] ?? null;

  useEffect(() => {
    void loadReview(params.jobId);
  }, [params.jobId]);

  useEffect(() => {
    if (!note || markdown === note.markdown) {
      return;
    }
    const timer = setTimeout(async () => {
      const saved = await putNote(params.jobId, note.etag, markdown);
      setNote(saved);
    }, AUTOSAVE_MS);
    return () => clearTimeout(timer);
  }, [markdown, note, params.jobId]);

  async function loadReview(jobId: string) {
    const [nextNote, nextClips, nextVersions] = await Promise.all([
      getNote(jobId),
      getClips(jobId),
      listVersions(jobId),
    ]);
    setNote(nextNote);
    setMarkdown(nextNote.markdown);
    setClipsView(nextClips);
    setCaption(nextClips.clips[0]?.scene_caption ?? "");
    setVersions(nextVersions);
  }

  async function toggleSummary() {
    if (!note) {
      return;
    }
    await patchContent({ include_summary: !note.include_summary });
  }

  async function toggleTranscript() {
    if (!note) {
      return;
    }
    await patchContent({ include_transcript: !note.include_transcript });
  }

  async function patchContent(body: { include_summary?: boolean; include_transcript?: boolean }) {
    if (!note) {
      return;
    }
    try {
      const updated = await patchNote(params.jobId, note.etag, body);
      setNote(updated);
      setMarkdown(updated.markdown);
      setError("");
    } catch {
      setError("Content selection must include summary or transcript.");
    }
  }

  async function saveCaption() {
    if (!clip) {
      return;
    }
    const updated = await patchClip(clip.id, clip.etag, { scene_caption: caption });
    setClipsView((current) =>
      current
        ? {
            ...current,
            clips: current.clips.map((item) => (item.id === updated.id ? updated : item)),
          }
        : current,
    );
  }

  async function rebuild() {
    if (!note) {
      return;
    }
    const updated = await rebuildNote(params.jobId, note.etag);
    setNote(updated);
    setMarkdown(updated.markdown);
  }

  async function keep() {
    if (!note) {
      return;
    }
    const updated = await keepNote(params.jobId, note.etag);
    setNote(updated);
  }

  async function saveCurrentVersion() {
    if (!note || !clipsView) {
      return;
    }
    const saved = await saveVersion(params.jobId, note.etag, clipsView.collection_etag, null);
    setVersions((current) => [...current, saved]);
  }

  async function restore(seq: number) {
    if (!note || !clipsView) {
      return;
    }
    await restoreVersion(params.jobId, seq, note.etag, clipsView.collection_etag);
  }

  const preview = useMemo(() => renderPreview(note, markdown), [note, markdown]);

  if (!note) {
    return <main className="review-shell">Loading review</main>;
  }

  return (
    <main className="review-shell">
      <header className="review-header">
        <h1>Review note</h1>
      </header>

      {note.clips_dirty ? (
        <section className="rebuild-banner">
          <p>Clips changed since this note was polished</p>
          <button onClick={rebuild} type="button">
            Rebuild
          </button>
          <button onClick={keep} type="button">
            Keep my note
          </button>
        </section>
      ) : null}

      <ContentSelector
        includeSummary={note.include_summary}
        includeTranscript={note.include_transcript}
        onToggleSummary={toggleSummary}
        onToggleTranscript={toggleTranscript}
      />
      {error ? <p role="alert">{error}</p> : null}

      {clip ? (
        <section className="caption-editor">
          <label>
            Scene caption
            <input onChange={(event) => setCaption(event.target.value)} value={caption} />
          </label>
          <button onClick={saveCaption} type="button">
            Save caption
          </button>
        </section>
      ) : null}

      <DocEditor
        excluded={!note.include_summary}
        markdown={markdown}
        onChange={(value) => setMarkdown(value)}
      />

      <section className="live-preview" aria-label="Live preview">
        <div className="preview-body">{preview}</div>
        {note.include_transcript ? (
          <blockquote aria-readonly="true">Transcript projected from clip spans.</blockquote>
        ) : null}
      </section>

      <VersionHistory versions={versions} onSave={saveCurrentVersion} onRestore={restore} />
    </main>
  );
}

function renderPreview(note: NoteView | null, markdown: string) {
  if (!note?.include_summary) {
    return "";
  }
  return markdown;
}
