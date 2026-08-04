export type RouteStatus = "accepted" | "quarantined";

export interface RouteResult {
  id: string;
  topic: string;
  topic_label: string;
  status: RouteStatus;
  message: string;
  confidence: number;
  filename: string;
  routed_at: string;
}

export interface FileListItem {
  id: string;
  filename: string;
  topic: string;
  topic_label: string;
  routed_at: string;
}

export interface FilesResponse {
  doc_center: FileListItem[];
  quarantine: FileListItem[];
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
  if (input.file) {
    form.append("file", input.file);
  }
  if (input.text && input.text.trim()) {
    form.append("text", input.text.trim());
  }

  const res = await fetch("/api/route", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    throw new Error(await readError(res));
  }
  return res.json();
}

export async function fetchFiles(): Promise<FilesResponse> {
  const res = await fetch("/api/files");
  if (!res.ok) {
    throw new Error(await readError(res));
  }
  return res.json();
}
