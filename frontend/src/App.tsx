import { useCallback, useEffect, useState } from "react";
import {
  fetchFiles,
  routeArticle,
  type FileListItem,
  type RouteResult,
} from "./api";
import { DestinationLists } from "./components/DestinationLists";
import { ResultPanel } from "./components/ResultPanel";
import { UploadPanel } from "./components/UploadPanel";
import "./App.css";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RouteResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [docCenter, setDocCenter] = useState<FileListItem[]>([]);
  const [quarantine, setQuarantine] = useState<FileListItem[]>([]);

  const refreshFiles = useCallback(async () => {
    try {
      const data = await fetchFiles();
      setDocCenter(data.doc_center);
      setQuarantine(data.quarantine);
    } catch {
      // Lists are secondary; keep last known state on refresh failure.
    }
  }, []);

  useEffect(() => {
    void refreshFiles();
  }, [refreshFiles]);

  function handleFileChange(next: File | null) {
    setFile(next);
    setResult(null);
    setError(null);
  }

  function handleTextChange(next: string) {
    setText(next);
    setResult(null);
    setError(null);
  }

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const routed = await routeArticle({ file, text });
      setResult(routed);
      await refreshFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Routing failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <p className="hero__brand">Doc Center Router</p>
        <p className="hero__tagline">
          Route articles into the Doc Center or Quarantine using topic
          classification.
        </p>
      </header>

      <main className="main">
        <UploadPanel
          file={file}
          text={text}
          loading={loading}
          onFileChange={handleFileChange}
          onTextChange={handleTextChange}
          onSubmit={() => void handleSubmit()}
        />
        <ResultPanel result={result} error={error} />
        <DestinationLists docCenter={docCenter} quarantine={quarantine} />
      </main>
    </div>
  );
}
