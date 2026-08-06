import type { FileListItem, Role } from "../api";

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function StorageBay({
  title,
  path,
  items,
  tone,
  selectedId,
  onSelect,
}: {
  title: string;
  path: string;
  items: FileListItem[];
  tone: "doc" | "quarantine";
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <article className={`storage-bay storage-bay--${tone}`}>
      <header className="storage-bay__header">
        <div className="storage-bay__identity">
          <span className="storage-bay__glyph" aria-hidden="true" />
          <div>
            <p className="storage-bay__kicker">Storage</p>
            <h3 className="storage-bay__title">{title}</h3>
          </div>
        </div>
        <div className="storage-bay__stats">
          <span className="storage-bay__count">{items.length}</span>
          <span className="storage-bay__count-label">files</span>
        </div>
      </header>

      <p className="storage-bay__path">{path}</p>

      <div className="storage-bay__body">
        {items.length === 0 ? (
          <p className="storage-bay__empty">Empty — no files in this space</p>
        ) : (
          <ul className="storage-bay__list">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={`storage-bay__item${selectedId === item.id ? " is-selected" : ""}`}
                  onClick={() => onSelect(item.id)}
                >
                  <span className="storage-bay__file-icon" aria-hidden="true" />
                  <span className="storage-bay__file-copy">
                    <span className="storage-bay__filename">{item.filename}</span>
                    <span className="storage-bay__meta">
                      {item.topic_label} · {(item.confidence * 100).toFixed(0)}%
                      {" · "}
                      <time dateTime={item.routed_at}>
                        {relativeTime(item.routed_at)}
                      </time>
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  );
}

function ReviewQueue({
  items,
  selectedId,
  onSelect,
}: {
  items: FileListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="work-queue" aria-labelledby="work-queue-heading">
      <div className="work-queue__intro">
        <div>
          <p className="work-queue__kicker">Working queue</p>
          <h2 id="work-queue-heading" className="work-queue__heading">
            Needs review
          </h2>
          <p className="work-queue__sub">
            Low-confidence predictions wait here until a reviewer accepts them
            into Doc Center or rejects them to Quarantine.
          </p>
        </div>
        <div className="work-queue__badge">
          <span className="work-queue__badge-count">{items.length}</span>
          <span className="work-queue__badge-label">pending</span>
        </div>
      </div>

      <div className="work-queue__tray">
        {items.length === 0 ? (
          <p className="work-queue__empty">Queue clear — nothing pending</p>
        ) : (
          <ul className="work-queue__list">
            {items.map((item, index) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={`work-queue__item${selectedId === item.id ? " is-selected" : ""}`}
                  onClick={() => onSelect(item.id)}
                >
                  <span className="work-queue__pos">{index + 1}</span>
                  <span className="work-queue__copy">
                    <span className="work-queue__filename">{item.filename}</span>
                    <span className="work-queue__meta">
                      Suggested: {item.topic_label} ·{" "}
                      {(item.confidence * 100).toFixed(0)}% confidence
                      {" · "}
                      <time dateTime={item.routed_at}>
                        {relativeTime(item.routed_at)}
                      </time>
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

type DestinationListsProps = {
  role: Role;
  docCenter: FileListItem[];
  needsReview: FileListItem[];
  quarantine: FileListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
};

export function DestinationLists({
  role,
  docCenter,
  needsReview,
  quarantine,
  selectedId,
  onSelect,
}: DestinationListsProps) {
  const isReviewer = role === "reviewer";

  return (
    <div className="destinations">
      {isReviewer ? (
        <ReviewQueue
          items={needsReview}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      ) : null}

      <section className="storage" aria-labelledby="storage-heading">
        <div className="storage__intro">
          <h2 id="storage-heading" className="storage__heading">
            {isReviewer ? "Final storage" : "Doc Center storage"}
          </h2>
          <p className="storage__sub">
            {isReviewer
              ? "Settled destinations after auto-routing or reviewer action."
              : "Accepted documents live here. Your last upload outcome appears above."}
          </p>
        </div>

        <div
          className={`storage__grid${isReviewer ? " storage__grid--two" : ""}`}
        >
          <StorageBay
            title="Doc Center"
            path="/doc-center"
            items={docCenter}
            tone="doc"
            selectedId={selectedId}
            onSelect={onSelect}
          />
          {isReviewer ? (
            <StorageBay
              title="Quarantine"
              path="/quarantine"
              items={quarantine}
              tone="quarantine"
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ) : null}
        </div>
      </section>
    </div>
  );
}
