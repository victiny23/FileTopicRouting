import { useState } from "react";
import type { RouteResult } from "../api";

type ResultPanelProps = {
  result: RouteResult | null;
  error: string | null;
};

export function ResultPanel({ result, error }: ResultPanelProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  if (error) {
    return (
      <section className="result-panel result-panel--error" role="alert">
        <p className="result-panel__message">{error}</p>
      </section>
    );
  }

  if (!result) return null;

  const accepted = result.status === "accepted";

  return (
    <section
      className={`result-panel ${accepted ? "result-panel--accepted" : "result-panel--quarantined"}`}
      aria-live="polite"
    >
      <p className="result-panel__status">
        {accepted ? "Accepted to Doc Center" : "Moved to Quarantine"}
      </p>
      <p className="result-panel__message">{result.message}</p>
      <p className="result-panel__meta">
        Topic: {result.topic_label}
        <span aria-hidden="true"> · </span>
        Confidence: {(result.confidence * 100).toFixed(1)}%
      </p>
      <button
        type="button"
        className="result-panel__details-toggle"
        aria-expanded={detailsOpen}
        onClick={() => setDetailsOpen((v) => !v)}
      >
        {detailsOpen ? "Hide details" : "Details"}
      </button>
      {detailsOpen ? (
        <dl className="result-panel__details">
          <div>
            <dt>Filename</dt>
            <dd>{result.filename}</dd>
          </div>
          <div>
            <dt>Predicted topic</dt>
            <dd>{result.topic}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{(result.confidence * 100).toFixed(1)}%</dd>
          </div>
        </dl>
      ) : null}
    </section>
  );
}
