"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { ClipsView, NoteView, exportJob, getClips, getNote } from "../../../lib/api";
import { followDownload } from "../../../lib/navigation";

export function ExportClient({ jobId }: { jobId: string }) {
  const [clipsView, setClipsView] = useState<ClipsView | null>(null);
  const [note, setNote] = useState<NoteView | null>(null);

  useEffect(() => {
    void loadExport(jobId);
  }, [jobId]);

  async function loadExport(jobId: string) {
    const [nextClips, nextNote] = await Promise.all([getClips(jobId), getNote(jobId)]);
    setClipsView(nextClips);
    setNote(nextNote);
  }

  async function download() {
    const response = await exportJob(jobId);
    followDownload(response.download_url);
  }

  const sectionCount = useMemo(
    () => (note ? (note.markdown.match(/^## /gm) ?? []).length : 0),
    [note],
  );
  const screenshotCount = clipsView?.clips.filter((clip) => clip.scene_url).length ?? 0;
  const filename = `video-to-note-${jobId}.zip`;
  const sizeLabel = note ? `${Math.max(1, Math.ceil(note.markdown.length / 1024))} KB estimate` : "";

  return (
    <main className="export-shell">
      <header>
        <h1>Export note</h1>
      </header>

      <section className="export-summary" aria-label="Export summary">
        <h2>{filename}</h2>
        <p>{sectionCount} sections</p>
        <p>{screenshotCount} screenshots</p>
        <p>{sizeLabel}</p>
      </section>

      <section className="zip-contents" aria-label="ZIP contents">
        <h2>ZIP contents</h2>
        <ul>
          <li>note.md</li>
          <li>images/</li>
          <li>metadata.json</li>
        </ul>
      </section>

      <div className="export-actions">
        <button onClick={download} type="button">
          Download ZIP
        </button>
        <Link href="/submit">Start a new note</Link>
      </div>
    </main>
  );
}
