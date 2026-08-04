import { useId, useRef, useState } from "react";

const ACCEPTED = ".txt,.md,.pdf";

type UploadPanelProps = {
  file: File | null;
  text: string;
  loading: boolean;
  onFileChange: (file: File | null) => void;
  onTextChange: (text: string) => void;
  onSubmit: () => void;
};

export function UploadPanel({
  file,
  text,
  loading,
  onFileChange,
  onTextChange,
  onSubmit,
}: UploadPanelProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const canSubmit = Boolean(file) || text.trim().length > 0;

  function takeFile(next: File | null) {
    if (!next) {
      onFileChange(null);
      return;
    }
    const lower = next.name.toLowerCase();
    if (
      !lower.endsWith(".txt") &&
      !lower.endsWith(".md") &&
      !lower.endsWith(".pdf")
    ) {
      onFileChange(null);
      return;
    }
    onFileChange(next);
  }

  return (
    <section className="upload-panel" aria-labelledby="upload-heading">
      <h2 id="upload-heading" className="visually-hidden">
        Upload article
      </h2>

      <div
        className={`dropzone${dragging ? " dropzone--active" : ""}${file ? " dropzone--filled" : ""}`}
        onDragEnter={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const dropped = e.dataTransfer.files?.[0] ?? null;
          takeFile(dropped);
        }}
      >
        <input
          ref={inputRef}
          id={inputId}
          className="dropzone__input"
          type="file"
          accept={ACCEPTED}
          onChange={(e) => takeFile(e.target.files?.[0] ?? null)}
        />
        <label htmlFor={inputId} className="dropzone__label">
          <span className="dropzone__title">Drop an article here</span>
          <span className="dropzone__hint">
            .txt, .md, or .pdf — or click to browse
          </span>
        </label>
      </div>

      {file ? (
        <div className="file-chip">
          <span className="file-chip__name">{file.name}</span>
          <button
            type="button"
            className="file-chip__clear"
            onClick={() => {
              onFileChange(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
            aria-label="Remove selected file"
          >
            Clear
          </button>
        </div>
      ) : null}

      <div className="divider" role="separator">
        <span>or paste article text</span>
      </div>

      <label className="paste-label" htmlFor="paste-text">
        Article text
      </label>
      <textarea
        id="paste-text"
        className="paste-area"
        rows={8}
        placeholder="Paste the full article body here…"
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
      />

      <button
        type="button"
        className="route-btn"
        disabled={!canSubmit || loading}
        onClick={onSubmit}
      >
        {loading ? "Routing…" : "Route file"}
      </button>
    </section>
  );
}
