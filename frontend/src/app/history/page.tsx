"use client";

import { useEffect, useMemo, useState } from "react";
import { Card, Button, Badge } from "@/components/ui";
import { deleteDataset, listDatasets, type DatasetListItem } from "@/lib/api";

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function HistoryPage() {
  const [items, setItems] = useState<DatasetListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setErr(null);
    try {
      const res = await listDatasets();
      setItems(res.items ?? []);
    } catch (e: any) {
      const msg = String(e?.message ?? "");
      if (msg.includes("(401)") || msg.toLowerCase().includes("missing bearer token")) {
        window.location.href = `/login?next=${encodeURIComponent("/history")}`;
        return;
      }
      setErr(e?.message ?? "Failed to load history.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const empty = useMemo(() => !loading && !err && items.length === 0, [loading, err, items.length]);

  async function onDelete(id: string) {
    const ok = window.confirm("Delete this dataset history? This removes the upload, analysis, and chat history.");
    if (!ok) return;
    setBusyId(id);
    try {
      await deleteDataset(id);
      await refresh();
    } catch (e: any) {
      alert(e?.message ?? "Delete failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-14">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-2xl font-semibold tracking-tight text-fg">History</div>
          <div className="mt-1 text-sm text-fg-muted">Pick up where things left off—uploads, dashboards, and chats.</div>
        </div>
        <div className="flex items-center gap-2">
          <a href="/">
            <Button variant="secondary">Upload new</Button>
          </a>
          <Button onClick={refresh} disabled={loading}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="mt-8">
        {loading ? (
          <Card className="p-6">
            <div className="text-sm text-fg-muted">Loading history…</div>
          </Card>
        ) : null}
        {err ? (
          <Card className="p-6">
            <div className="text-sm font-semibold text-fg">Couldn’t load history</div>
            <div className="mt-2 text-sm text-fg-muted">{err}</div>
            <div className="mt-4">
              <Button onClick={refresh}>Retry</Button>
            </div>
          </Card>
        ) : null}
        {empty ? (
          <Card className="p-6">
            <div className="text-sm font-semibold text-fg">No history yet</div>
            <div className="mt-2 text-sm text-fg-muted">Upload a CSV/Excel to create your first dashboard.</div>
            <div className="mt-4">
              <a href="/">
                <Button>Upload</Button>
              </a>
            </div>
          </Card>
        ) : null}

        {!loading && !err && items.length ? (
          <div className="grid grid-cols-1 gap-4">
            {items.map((it) => (
              <Card key={it.dataset_id} className="p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="text-sm font-semibold text-fg truncate">{it.original_filename}</div>
                      <Badge>{it.rows != null ? `${it.rows.toLocaleString()} rows` : "—"}</Badge>
                      <Badge>{it.cols != null ? `${it.cols} cols` : "—"}</Badge>
                      <Badge>chat saved</Badge>
                    </div>
                    <div className="mt-1 text-xs text-fg-muted">
                      {formatTime(it.created_at)} • Dataset{" "}
                      <span className="font-mono text-fg/70">{it.dataset_id.slice(0, 8)}…</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <a href={`/d/${encodeURIComponent(it.dataset_id)}?share=${encodeURIComponent(it.share_id)}`}>
                      <Button>Open</Button>
                    </a>
                    <a href={`/s/${encodeURIComponent(it.share_id)}`}>
                      <Button variant="secondary">Share link</Button>
                    </a>
                    <Button variant="danger" onClick={() => void onDelete(it.dataset_id)} disabled={busyId === it.dataset_id}>
                      {busyId === it.dataset_id ? "Deleting…" : "Delete"}
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : null}
      </div>
    </main>
  );
}


