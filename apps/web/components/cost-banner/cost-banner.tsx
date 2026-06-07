import type { CostEstimate } from "../../lib/api";

export function CostBanner({ estimate }: { estimate: CostEstimate | null }) {
  if (!estimate) {
    return null;
  }

  const breakdown = estimate.breakdown ?? {};
  return (
    <aside className="cost-banner" aria-label="Cost estimate">
      <strong>{estimate.usd ? `$${estimate.usd}` : "Estimate pending"}</strong>
      <span>
        {formatNumber(breakdown.expected_clips)} clips · {formatNumber(breakdown.llm_calls)} LLM
        calls · {formatNumber(breakdown.ocr_frames)} OCR frames
      </span>
    </aside>
  );
}

function formatNumber(value: unknown): string {
  return typeof value === "number" || typeof value === "string" ? String(value) : "0";
}
