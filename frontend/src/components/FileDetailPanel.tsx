import { useEffect } from "react";
import type { FileDetail, Role } from "../api";
import { ContributionChart } from "./ContributionChart";

type FileDetailPanelProps = {
  open: boolean;
  detail: FileDetail | null;
  loading: boolean;
  error: string | null;
  role: Role;
  actionLoading: boolean;
  onAccept: () => void;
  onReject: () => void;
  onClose: () => void;
};

const STATUS_LABEL: Record<string, string> = {
  accepted: "Doc Center",
  needs_review: "Needs review",
  quarantined: "Quarantine",
};

export function FileDetailPanel({
  open,
  detail,
  loading,
  error,
  role,
  actionLoading,
  onAccept,
  onReject,
  onClose,
}: FileDetailPanelProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open) return null;

  const canAct =
    role === "reviewer" && detail?.status === "needs_review" && !actionLoading;

  return (
    <div className="drawer" role="presentation">
      <button
        type="button"
        className="drawer__backdrop"
        aria-label="Close file review"
        onClick={onClose}
      />
      <aside
        className="drawer__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-heading"
      >
        <div className="drawer__head">
          <div>
            <p className="drawer__kicker">File review</p>
            <h2 id="detail-heading" className="drawer__title">
              {detail?.filename ?? (loading ? "Loading…" : "File detail")}
            </h2>
            {detail ? (
              <p className="drawer__sub">
                {STATUS_LABEL[detail.status]} · {detail.topic_label} ·{" "}
                {(detail.confidence * 100).toFixed(1)}% confidence
                {detail.decision_source !== "auto"
                  ? ` · ${detail.decision_source}`
                  : ""}
              </p>
            ) : null}
          </div>
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="drawer__content">
          {loading ? <p className="drawer__loading">Loading…</p> : null}
          {error ? (
            <p className="drawer__error" role="alert">
              {error}
            </p>
          ) : null}

          {detail ? (
            <>
              <section className="drawer__section">
                <h3 className="drawer__section-title">Article</h3>
                <pre className="drawer__text">{detail.article_text}</pre>
              </section>
              <section className="drawer__section">
                <ContributionChart
                  contributions={detail.contributions}
                  title="Evidence for predicted topic"
                />
              </section>
            </>
          ) : null}
        </div>

        {role === "reviewer" && detail?.status === "needs_review" ? (
          <div className="drawer__footer">
            <p className="drawer__hint">
              Model suggestion: {detail.topic_label}. Accept → Doc Center;
              reject → Quarantine.
            </p>
            <div className="drawer__buttons">
              <button
                type="button"
                className="btn btn--primary"
                disabled={!canAct}
                onClick={onAccept}
              >
                {actionLoading ? "Working…" : "Accept to Doc Center"}
              </button>
              <button
                type="button"
                className="btn btn--danger"
                disabled={!canAct}
                onClick={onReject}
              >
                Reject to Quarantine
              </button>
            </div>
          </div>
        ) : null}
      </aside>
    </div>
  );
}
