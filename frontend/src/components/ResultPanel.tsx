import type { RouteResult } from "../api";
import { ContributionChart } from "./ContributionChart";

type ResultPanelProps = {
  result: RouteResult | null;
  error: string | null;
};

const STATUS_COPY: Record<string, string> = {
  accepted: "Accepted to Doc Center",
  needs_review: "Sent to Needs review",
  quarantined: "Moved to Quarantine",
};

export function ResultPanel({ result, error }: ResultPanelProps) {
  if (error) {
    return (
      <section className="result-panel result-panel--error" role="alert">
        <p className="result-panel__eyebrow">Upload failed</p>
        <p className="result-panel__message">{error}</p>
      </section>
    );
  }

  if (!result) return null;

  return (
    <section
      className={`result-panel result-panel--${result.status}`}
      aria-live="polite"
    >
      <p className="result-panel__eyebrow">{STATUS_COPY[result.status]}</p>
      <p className="result-panel__message">{result.message}</p>
      <div className="result-panel__meta-row">
        <span>Topic · {result.topic_label}</span>
        <span>
          Confidence · {(result.confidence * 100).toFixed(1)}%
          {result.tau != null ? ` (τ ${result.tau.toFixed(2)})` : ""}
        </span>
      </div>
      {result.contributions?.length ? (
        <ContributionChart contributions={result.contributions} />
      ) : null}
    </section>
  );
}
