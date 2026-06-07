export type TimelineState = {
  videoReady: boolean;
  transcriptReady: boolean;
  screenshotsReady: boolean;
  clipsReady: boolean;
  readyClips: number[];
  reviewReady: boolean;
};

export function ProgressiveTimeline({ state }: { state: TimelineState }) {
  return (
    <section className="timeline-grid" aria-label="Timeline">
      <Lane
        title="Screenshot"
        value={state.screenshotsReady ? "Screenshots ready" : "Placeholder thumbnails"}
      />
      <Lane title="Clips" value={state.clipsReady ? "Clip boundaries ready" : "Timeline empty"} />
      <Lane
        title="Transcript"
        value={state.transcriptReady ? "Transcript ready" : "Transcript rows blank"}
      />
      <Lane
        title="Summary/Notes"
        value={
          state.readyClips.length
            ? state.readyClips.map((index) => `Clip ${index + 1} summary ready`).join(", ")
            : "Summary skeletons pending"
        }
      />
      <Lane title="Video" value={state.videoReady ? "Video ready" : "Preparing video"} />
    </section>
  );
}

function Lane({ title, value }: { title: string; value: string }) {
  return (
    <article className="timeline-lane">
      <h2>{title}</h2>
      <p>{value}</p>
    </article>
  );
}
