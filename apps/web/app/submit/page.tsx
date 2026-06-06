"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { CostBanner } from "../../components/cost-banner/cost-banner";
import {
  ApiError,
  CostEstimate,
  ExampleNote,
  PromptDepth,
  createJob,
} from "../../lib/api";

export const MAX_EXAMPLE_BYTES = 256 * 1024;

const DEPTHS: Array<{ label: string; value: PromptDepth }> = [
  { label: "Thorough", value: "thorough" },
  { label: "Balanced", value: "balanced" },
  { label: "Brief", value: "brief" },
  { label: "I'll prompt it", value: "custom" },
];

export default function SubmitPage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [depth, setDepth] = useState<PromptDepth>("balanced");
  const [customPrompt, setCustomPrompt] = useState("");
  const [useSavedStyle, setUseSavedStyle] = useState(false);
  const [saveAsDefault, setSaveAsDefault] = useState(false);
  const [examples, setExamples] = useState<ExampleNote[]>([]);
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function chooseExamples(event: ChangeEvent<HTMLInputElement>) {
    setError("");
    const files = Array.from(event.target.files ?? []);
    const rejected = files.find((file) => !file.name.toLowerCase().endsWith(".md"));
    if (rejected) {
      setExamples([]);
      setError("Only .md files are supported.");
      return;
    }
    const oversized = files.find((file) => file.size > MAX_EXAMPLE_BYTES);
    if (oversized) {
      setExamples([]);
      setError("Example file is too large.");
      return;
    }

    setExamples(
      await Promise.all(
        files.map(async (file) => ({
          content: await readFileText(file),
          filename: file.name,
          save_as_default: saveAsDefault,
        })),
      ),
    );
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const response = await createJob({
        custom_prompt: depth === "custom" ? customPrompt : null,
        depth,
        examples: examples.map((example) => ({
          ...example,
          save_as_default: saveAsDefault,
        })),
        url,
        use_saved_style: useSavedStyle,
      });
      setEstimate(response.cost_estimate);
      router.push(`/edit/${response.job_id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not create note");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="submit-shell">
      <form className="submit-surface" onSubmit={submit}>
        <header>
          <h1>Create note</h1>
        </header>

        <label>
          Video URL
          <input
            name="url"
            onChange={(event) => setUrl(event.target.value)}
            required
            type="url"
            value={url}
          />
        </label>

        <fieldset>
          <legend>Depth</legend>
          <div className="segmented">
            {DEPTHS.map((option) => (
              <label key={option.value}>
                <input
                  checked={depth === option.value}
                  name="depth"
                  onChange={() => setDepth(option.value)}
                  type="radio"
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        {depth === "custom" ? (
          <label>
            Custom prompt
            <textarea
              name="custom_prompt"
              onChange={(event) => setCustomPrompt(event.target.value)}
              required
              rows={4}
              value={customPrompt}
            />
          </label>
        ) : null}

        <section className="style-panel" aria-label="Match my style">
          <label>
            <input
              checked={useSavedStyle}
              onChange={(event) => setUseSavedStyle(event.target.checked)}
              type="checkbox"
            />
            Use saved style
          </label>

          <label>
            Add Markdown examples
            <input
              accept=".md,text/markdown,text/x-markdown"
              multiple
              onChange={chooseExamples}
              type="file"
            />
          </label>
          {examples.length ? <span>{examples.length} example ready</span> : null}

          <label>
            <input
              checked={saveAsDefault}
              onChange={(event) => setSaveAsDefault(event.target.checked)}
              type="checkbox"
            />
            Save as my default style
          </label>
        </section>

        {error ? <p role="alert">{error}</p> : null}
        <CostBanner estimate={estimate} />

        <button disabled={pending} type="submit">
          {pending ? "Creating" : "Create note"}
        </button>
      </form>
    </main>
  );
}

function readFileText(file: File): Promise<string> {
  if ("text" in file && typeof file.text === "function") {
    return file.text();
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error("Could not read file"));
    reader.readAsText(file);
  });
}
