import { useCallback, useEffect, useRef, useState } from "react";
import {
  acceptFile,
  fetchConfig,
  fetchFile,
  fetchFiles,
  rejectFile,
  routeArticle,
  updateTau,
  type FileDetail,
  type FileListItem,
  type Role,
  type RouteResult,
} from "./api";
import { AppHeader } from "./components/AppHeader";
import { DestinationLists } from "./components/DestinationLists";
import { FileDetailPanel } from "./components/FileDetailPanel";
import { ResultPanel } from "./components/ResultPanel";
import { UploadPanel } from "./components/UploadPanel";
import "./App.css";

export default function App() {
  const [role, setRole] = useState<Role>("user");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RouteResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [docCenter, setDocCenter] = useState<FileListItem[]>([]);
  const [needsReview, setNeedsReview] = useState<FileListItem[]>([]);
  const [quarantine, setQuarantine] = useState<FileListItem[]>([]);

  const [tau, setTau] = useState(0.26);
  const [defaultTau, setDefaultTau] = useState(0.26);
  const skipTauPersist = useRef(true);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<FileDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const refreshFiles = useCallback(async () => {
    try {
      const data = await fetchFiles();
      setDocCenter(data.doc_center);
      setNeedsReview(data.needs_review);
      setQuarantine(data.quarantine);
    } catch {
      // keep last known lists
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const cfg = await fetchConfig();
        skipTauPersist.current = true;
        setTau(cfg.tau);
        setDefaultTau(cfg.default_tau);
      } catch {
        // defaults remain
      }
      await refreshFiles();
    })();
  }, [refreshFiles]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      setDetailLoading(true);
      setDetailError(null);
      try {
        const next = await fetchFile(selectedId);
        if (!cancelled) setDetail(next);
      } catch (err) {
        if (!cancelled) {
          setDetail(null);
          setDetailError(
            err instanceof Error ? err.message : "Failed to load file.",
          );
        }
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  // When switching to user role, clear selection if it was quarantine/review only
  useEffect(() => {
    if (role === "user" && detail && detail.status !== "accepted") {
      setSelectedId(null);
    }
  }, [role, detail]);

  // Persist tau after reviewer adjusts the slider (skip hydrate / reset echoes).
  useEffect(() => {
    if (skipTauPersist.current) {
      skipTauPersist.current = false;
      return;
    }
    let cancelled = false;
    const handle = window.setTimeout(() => {
      void (async () => {
        try {
          const cfg = await updateTau(tau);
          if (!cancelled) {
            skipTauPersist.current = true;
            setTau(cfg.tau);
            setDefaultTau(cfg.default_tau);
          }
        } catch {
          // leave local value; reviewer can retry
        }
      })();
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [tau]);

  function handleTauReset() {
    skipTauPersist.current = false;
    setTau(defaultTau);
  }
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
      setSelectedId(routed.id);
      await refreshFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Routing failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAccept() {
    if (!selectedId) return;
    setActionLoading(true);
    try {
      const updated = await acceptFile(selectedId);
      setDetail(updated);
      if (result?.id === selectedId) {
        setResult({
          ...result,
          status: updated.status,
          message: `This file has been accepted to the Doc Center by a reviewer.`,
          decision_source: updated.decision_source,
        });
      }
      await refreshFiles();
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "Accept failed.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject() {
    if (!selectedId) return;
    setActionLoading(true);
    try {
      const updated = await rejectFile(selectedId);
      setDetail(updated);
      if (result?.id === selectedId) {
        setResult({
          ...result,
          status: updated.status,
          message: `This file has been moved to Quarantine by a reviewer.`,
          decision_source: updated.decision_source,
        });
      }
      await refreshFiles();
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "Reject failed.");
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <AppHeader
        role={role}
        onRoleChange={setRole}
        tau={tau}
        defaultTau={defaultTau}
        onTauChange={setTau}
        onTauReset={handleTauReset}
        tauDisabled={false}
      />

      <main className="workspace">
        <div className="workspace__primary">
          <UploadPanel
            file={file}
            text={text}
            loading={loading}
            onFileChange={handleFileChange}
            onTextChange={handleTextChange}
            onSubmit={() => void handleSubmit()}
          />
          <ResultPanel result={result} error={error} />
        </div>

        <DestinationLists
          role={role}
          docCenter={docCenter}
          needsReview={needsReview}
          quarantine={quarantine}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />

        <FileDetailPanel
          open={selectedId !== null}
          detail={detail}
          loading={detailLoading}
          error={detailError}
          role={role}
          actionLoading={actionLoading}
          onAccept={() => void handleAccept()}
          onReject={() => void handleReject()}
          onClose={() => setSelectedId(null)}
        />
      </main>
    </div>
  );
}
