import type { FileListItem } from "../api";

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const seconds = Math.round((Date.now() - then) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function FileColumn({
  title,
  items,
  tone,
}: {
  title: string;
  items: FileListItem[];
  tone: "doc" | "quarantine";
}) {
  return (
    <div className={`file-column file-column--${tone}`}>
      <h3 className="file-column__title">
        {title}
        <span className="file-column__count">{items.length}</span>
      </h3>
      {items.length === 0 ? (
        <p className="file-column__empty">No files yet</p>
      ) : (
        <ul className="file-column__list">
          {items.map((item) => (
            <li key={item.id} className="file-column__item">
              <span className="file-column__filename">{item.filename}</span>
              <span className="file-column__topic">{item.topic_label}</span>
              <time
                className="file-column__time"
                dateTime={item.routed_at}
                title={item.routed_at}
              >
                {relativeTime(item.routed_at)}
              </time>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

type DestinationListsProps = {
  docCenter: FileListItem[];
  quarantine: FileListItem[];
};

export function DestinationLists({
  docCenter,
  quarantine,
}: DestinationListsProps) {
  return (
    <section className="destinations" aria-labelledby="destinations-heading">
      <h2 id="destinations-heading" className="destinations__heading">
        Session destinations
      </h2>
      <p className="destinations__sub">
        Files routed in this session. Lists reset when the API restarts.
      </p>
      <div className="destinations__grid">
        <FileColumn title="Doc Center" items={docCenter} tone="doc" />
        <FileColumn title="Quarantine" items={quarantine} tone="quarantine" />
      </div>
    </section>
  );
}
