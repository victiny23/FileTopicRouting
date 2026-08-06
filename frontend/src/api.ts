export type RouteStatus = "accepted" | "quarantined" | "needs_review";
export type Role = "user" | "reviewer";

export interface TokenContribution {
  token: string;
  tfidf: number;
  coef: number;
  contribution: number;
}

export interface RouteResult {
  id: string;
  topic: string;
  topic_label: string;
  status: RouteStatus;
  message: string;
  confidence: number;
  filename: string;
  routed_at: string;
  tau: number;
  decision_source: string;
  contributions: TokenContribution[];
}

export interface FileListItem {
  id: string;
  filename: string;
  topic: string;
  topic_label: string;
  status: RouteStatus;
  confidence: number;
  routed_at: string;
  decision_source: string;
  reviewed_at: string | null;
}

export interface FileDetail extends FileListItem {
  article_text: string;
  contributions: TokenContribution[];
}

export interface FilesResponse {
  doc_center: FileListItem[];
  needs_review: FileListItem[];
  quarantine: FileListItem[];
}

export interface AppConfig {
  tau: number;
  default_tau: number;
}

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((d: { msg?: string }) => d.msg ?? String(d))
        .join("; ");
    }
    return JSON.stringify(data);
  } catch {
    return res.statusText || "Request failed";
  }
}

export async function routeArticle(input: {
  file?: File | null;
  text?: string;
}): Promise<RouteResult> {
  const form = new FormData();
  if (input.file) form.append("file", input.file);
  if (input.text && input.text.trim()) form.append("text", input.text.trim());

  const res = await fetch("/api/route", { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchFiles(): Promise<FilesResponse> {
  const res = await fetch("/api/files");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchFile(id: string): Promise<FileDetail> {
  const res = await fetch(`/api/files/${id}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function fetchConfig(): Promise<AppConfig> {
  const res = await fetch("/api/config");
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function updateTau(tau: number): Promise<AppConfig> {
  const res = await fetch("/api/config/tau", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tau }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function acceptFile(id: string): Promise<FileDetail> {
  const res = await fetch(`/api/files/${id}/accept`, { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function rejectFile(id: string): Promise<FileDetail> {
  const res = await fetch(`/api/files/${id}/reject`, { method: "POST" });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}
