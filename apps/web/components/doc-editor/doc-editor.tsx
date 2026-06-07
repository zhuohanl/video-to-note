export function DocEditor({
  markdown,
  excluded,
  onChange,
}: {
  markdown: string;
  excluded: boolean;
  onChange: (markdown: string) => void;
}) {
  return (
    <section className="doc-editor" aria-label="Document editor">
      <div className="markdown-toolbar" aria-label="Markdown toolbar">
        <button type="button">H2</button>
        <button type="button">B</button>
        <button type="button">I</button>
        <button type="button">Code</button>
        <button type="button">List</button>
        <button type="button">Quote</button>
        <button type="button">Link</button>
        <button type="button">Divider</button>
      </div>
      {excluded ? <p>Summary excluded from output</p> : null}
      <label>
        Markdown editor
        <textarea
          aria-label="Markdown editor"
          onChange={(event) => onChange(event.target.value)}
          value={markdown}
        />
      </label>
    </section>
  );
}
