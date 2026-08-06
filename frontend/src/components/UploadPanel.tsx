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
    <section className="panel upload-panel" aria-labelledby="upload-heading">
      <div className="panel__head">
        <h2 id="upload-heading" className="panel__title">
          Submit article
        </h2>
        <p className="panel__sub">
          Upload .txt, .md, or .pdf — or paste text. Routing uses the current
          confidence threshold.
        </p>
      </div>

      <div
        className={`dropzone${dragging ? " is-active" : ""}${file ? " is-filled" : ""}`}
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
          takeFile(e.dataTransfer.files?.[0] ?? null);
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
          <span className="dropzone__title">Drop file or browse</span>
          <span className="dropzone__hint">.txt · .md · .pdf</span>
        </label>
      </div>

      {file ? (
        <div className="file-chip">
          <span className="file-chip__name">{file.name}</span>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              onFileChange(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
          >
            Clear
          </button>
        </div>
      ) : null}

      <div className="divider">
        <span>or paste text</span>
      </div>

      <div className="field-label-row">
        <label className="field-label" htmlFor="paste-text">
          Article text
        </label>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          disabled={!text}
          onClick={() => onTextChange("")}
        >
          Clear paste
        </button>
      </div>
      <textarea
        id="paste-text"
        className="paste-area"
        rows={7}
        placeholder="Paste article body…"
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
      />

      <button
        type="button"
        className="btn btn--primary btn--block"
        disabled={!canSubmit || loading}
        onClick={onSubmit}
      >
        {loading ? "Routing…" : "Route file"}
      </button>
    </section>
  );
}
