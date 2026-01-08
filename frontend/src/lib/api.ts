export type DatasetResponse = {
  dataset_id: string;
  share_id: string;
  analysis: any;
};

export type DatasetListItem = {
  dataset_id: string;
  share_id: string;
  original_filename: string;
  created_at: string;
  rows?: number | null;
  cols?: number | null;
};

export type DatasetListResponse = { items: DatasetListItem[] };

function getBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) return "http://localhost:8000";
  return base.replace(/\/+$/, "");
}

export const API_BASE_URL = getBaseUrl();

export async function uploadDataset(file: File): Promise<DatasetResponse> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE_URL}/api/datasets/upload`, {
    method: "POST",
    body: fd,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function getDataset(datasetId: string): Promise<DatasetResponse> {
  const res = await fetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Dataset not found (${res.status})`);
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
  const res = await fetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Chat failed (${res.status})`);
  }
  return res.json();
}

export async function listDatasets(): Promise<DatasetListResponse> {
  const res = await fetch(`${API_BASE_URL}/api/datasets`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load history (${res.status})`);
  return res.json();
}

export async function deleteDataset(datasetId: string): Promise<{ ok: boolean }> {
  const res = await fetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Delete failed (${res.status})`);
  }
  return res.json();
}

export async function getChatHistory(datasetId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}/chat/history`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Failed to load chat history (${res.status})`);
  return res.json();
}

export function reportPdfUrl(datasetId: string): string {
  return `${API_BASE_URL}/api/datasets/${encodeURIComponent(datasetId)}/report.pdf`;
}



