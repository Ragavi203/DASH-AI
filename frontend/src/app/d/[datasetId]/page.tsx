"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { DashboardShell } from "@/components/DashboardShell";
import { Card, Button, Badge } from "@/components/ui";
import { getDataset } from "@/lib/api";

export default function DatasetPage({ params }: { params: { datasetId: string } }) {
  const datasetId = params.datasetId;
  const search = useSearchParams();
  const share = search.get("share") || "";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any | null>(null);

  const shareId = useMemo(() => data?.share_id ?? share, [data, share]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        // Poll until ready (async processing)
        for (let i = 0; i < 120; i++) {
          const res = await getDataset(datasetId);
          if (cancelled) return;
          setData(res);
          const st = String(res?.status ?? "");
          if (!st || st === "ready") break;
          await new Promise((r) => setTimeout(r, 1500));
        }
      } catch (e: any) {
        const msg = String(e?.message ?? "");
        if (!cancelled && (msg.includes("(401)") || msg.toLowerCase().includes("missing bearer token"))) {
          window.location.href = `/login?next=${encodeURIComponent(`/d/${datasetId}`)}`;
          return;
        }
        if (!cancelled) setError(e?.message ?? "Failed to load dataset.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold text-fg">Building your dashboard…</div>
              <div className="mt-1 text-sm text-fg-muted">
                {data?.status === "processing"
                  ? "Upload received. Processing in the background — this page will refresh automatically."
                  : "Profiling columns, picking charts, finding anomalies."}
              </div>
            </div>
            <Badge>working</Badge>
          </div>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Skeleton />
            <Skeleton />
            <Skeleton />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Skeleton className="h-64" />
            <Skeleton className="h-64" />
          </div>
        </Card>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10">
        <Card className="p-6">
          <div className="text-lg font-semibold text-fg">Couldn’t load dashboard</div>
          <div className="mt-2 text-sm text-fg-muted">{error ?? "Unknown error."}</div>
          <div className="mt-6 flex gap-2">
            <Button variant="secondary" onClick={() => window.location.reload()}>
              Retry
            </Button>
            <a className="text-sm text-fg-muted hover:text-fg transition px-2 py-2" href="/">
              Back to upload →
            </a>
          </div>
        </Card>
      </main>
    );
  }

  return (
    <main>
      <DashboardShell datasetId={data.dataset_id} shareId={shareId} analysis={data.analysis} showShare />
    </main>
  );
}

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={[
        "h-24 rounded-2xl border border-card-border bg-card/40 animate-pulse",
        className ?? "",
      ].join(" ")}
    />
  );
}


