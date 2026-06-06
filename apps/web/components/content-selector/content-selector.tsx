export function ContentSelector({
  includeSummary,
  includeTranscript,
  onToggleSummary,
  onToggleTranscript,
}: {
  includeSummary: boolean;
  includeTranscript: boolean;
  onToggleSummary: () => void;
  onToggleTranscript: () => void;
}) {
  return (
    <fieldset className="content-selector">
      <legend>Content</legend>
      <label>
        <input
          checked={includeSummary}
          disabled={includeSummary && !includeTranscript}
          onChange={onToggleSummary}
          type="checkbox"
        />
        Summary
      </label>
      <label>
        <input
          checked={includeTranscript}
          disabled={includeTranscript && !includeSummary}
          onChange={onToggleTranscript}
          type="checkbox"
        />
        Transcript
      </label>
    </fieldset>
  );
}
