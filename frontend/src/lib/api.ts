export type DatasetResponse = {
  dataset_id: string;
  share_id: string;
  status?: string;
  error?: string | null;
  analysis: any;
};

export type DatasetListItem = {
  dataset_id: string;
  share_id: string;
  original_filename: string;
  created_at: string;
  status?: string | null;
  rows?: number | null;
  cols?: number | null;
  primary_metric?: string | null;
  health_score?: number | null;
  missing_pct?: number | null;
  duplicate_rows?: number | null;
  insight_count?: number | null;
};

export type DatasetListResponse = { items: DatasetListItem[] };

function getBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) return "http://localhost:8000";
  return base.replace(/\/+$/, "");
}

export const API_BASE_URL = getBaseUrl();

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem("dashai_token");
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (!token) window.localStorage.removeItem("dashai_token");
    else window.localStorage.setItem("dashai_token", token);
  } catch {
    // ignore
  }
}

async function authFetch(input: RequestInfo, init?: RequestInit): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {};
  const initHeaders = (init?.headers as any) || {};
  for (const [k, v] of Object.entries(initHeaders)) headers[k] = String(v);
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(input, { ...init, headers });
  // If token is invalid/expired, clear it so the app can recover cleanly.
  if (res.status === 401) {
    setToken(null);
  }
  return res;
}

async function errorFromResponse(res: Response, fallback: string): Promise<Error> {
  const status = res.status;
  try {
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const j = await res.json().catch(() => null);
      const detail = j?.detail ? String(j.detail) : JSON.stringify(j);
      return new Error(`${detail} (${status})`);
    }
  } catch {
    // ignore
  }
  const text = await res.text().catch(() => "");
  const msg = text ? String(text) : fallback;
  return new Error(`${msg} (${status})`);
}

export async function requestLoginCode(email: string): Promise<{ ok: boolean; dev_code?: string | null }> {
  const res = await fetch(`${API_BASE_URL}/api/auth/request_code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    throw await errorFromResponse(res, "Request code failed");
  }
  return res.json();
}

export async function verifyLoginCode(email: string, code: string): Promise<{ access_token: string }> {
  const res = await fetch(`${API_BASE_URL}/api/auth/verify_code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
  if (!res.ok) {
    throw await errorFromResponse(res, "Verify code failed");
  }
  return res.json();
}

export async function uploadDataset(file: File): Promise<DatasetResponse> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await authFetch(`${API_BASE_URL}/api/datasets/upload`, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) {
    throw await errorFromResponse(res, "Upload failed");
  }
  return res.json();
}

export async function getDataset(datasetId: string): Promise<DatasetResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw await errorFromResponse(res, "Dataset not found");
  return res.json();
}

export async function getSharedDataset(shareId: string): Promise<DatasetResponse> {
  const res = await fetch(`${API_BASE_URL}/api/share/${encodeURIComponent(shareId)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Share link not found (${res.status})`);
  return res.json();
}

export async function chat(datasetId: string, question: string): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    throw await errorFromResponse(res, "Chat failed");
  }
  return res.json();
}

export async function listDatasets(): Promise<DatasetListResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/datasets`, { cache: "no-store" });
  if (!res.ok) throw await errorFromResponse(res, "Failed to load history");
  return res.json();
}

export async function deleteDataset(datasetId: string): Promise<{ ok: boolean }> {
  const res = await authFetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}`, { method: "DELETE" });
  if (!res.ok) {
    throw await errorFromResponse(res, "Delete failed");
  }
  return res.json();
}

export async function getChatHistory(datasetId: string): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}/chat/history`, {
    cache: "no-store",
  });
  if (!res.ok) throw await errorFromResponse(res, "Failed to load chat history");
  return res.json();
}

export async function explainAnomaly(datasetId: string, anomalyIndex: number): Promise<any> {
  const res = await authFetch(
    `${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}/anomalies/${encodeURIComponent(String(anomalyIndex))}/explain`,
    { cache: "no-store" }
  );
  if (!res.ok) {
    throw await errorFromResponse(res, "Explain failed");
  }
  return res.json();
}

export async function pivot(datasetId: string, payload: any): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}/pivot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await errorFromResponse(res, "Pivot failed");
  return res.json();
}

export function reportPdfUrl(datasetId: string): string {
  return `${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}/report.pdf`;
}



