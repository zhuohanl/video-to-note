import type { VersionView } from "../../lib/api";

export function VersionHistory({
  versions,
  onSave,
  onRestore,
}: {
  versions: VersionView[];
  onSave: () => void;
  onRestore: (seq: number) => void;
}) {
  return (
    <section className="version-history" aria-label="Version history">
      <button onClick={onSave} type="button">
        Save version
      </button>
      {versions.map((version) => (
        <button key={version.seq} onClick={() => onRestore(version.seq)} type="button">
          Restore v{version.seq}
        </button>
      ))}
    </section>
  );
}
