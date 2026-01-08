"use client";

import { useEffect, useState } from "react";
import { DashboardShell } from "@/components/DashboardShell";
import { Card, Button, Badge } from "@/components/ui";
import { getSharedDataset } from "@/lib/api";

export default function SharedPage({ params }: { params: { shareId: string } }) {
  const shareId = params.shareId;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<any | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getSharedDataset(shareId);
        if (!cancelled) setData(res);
      } catch (e: any) {
        if (!cancelled) setError(e?.message ?? "Failed to load share link.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [shareId]);

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold text-fg">Loading shared dashboard…</div>
              <div className="mt-1 text-sm text-fg-muted">Fetching the latest saved analysis.</div>
            </div>
            <Badge>share</Badge>
          </div>
          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="h-64 rounded-2xl border border-card-border bg-card/40 animate-pulse" />
            <div className="h-64 rounded-2xl border border-card-border bg-card/40 animate-pulse" />
          </div>
        </Card>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-10">
        <Card className="p-6">
          <div className="text-lg font-semibold text-fg">Share link unavailable</div>
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
      <DashboardShell datasetId={data.dataset_id} shareId={data.share_id} analysis={data.analysis} showShare={false} />
    </main>
  );
}


