"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { UploadDropzone } from "@/components/UploadDropzone";
import { Badge, Button, Card } from "@/components/ui";
import { API_BASE_URL, uploadDataset } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<{ name: string; rows?: number; cols?: number } | null>(null);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    try {
      setAuthed(Boolean(window.localStorage.getItem("dashai_token")));
    } catch {
      setAuthed(false);
    }
  }, []);

  const primaryCtas = useMemo(() => {
    return authed
      ? [
          { label: "Upload a file", action: "scroll" as const },
          { label: "History", action: "nav" as const, href: "/history", variant: "secondary" as const },
        ]
      : [
          { label: "Login", action: "nav" as const, href: "/login", variant: "secondary" as const },
          { label: "Upload a file", action: "scroll" as const },
        ];
  }, [authed]);

  async function onFileSelected(file: File) {
    setBusy(true);
    try {
      const res = await uploadDataset(file);
      const shape = res?.analysis?.profile?.shape ?? {};
      setLast({ name: file.name, rows: shape.rows, cols: shape.cols });
      router.push(`/d/${res.dataset_id}?share=${encodeURIComponent(res.share_id)}`);
    } catch (e: any) {
      const msg = String(e?.message ?? "");
      if (msg.includes("(401)") || msg.toLowerCase().includes("missing bearer token")) {
        router.push(`/login?next=${encodeURIComponent("/")}`);
        return;
      }
      throw e;
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-14 sm:py-20">
      <section className="mx-auto max-w-4xl text-center">
        <div className="flex flex-wrap justify-center gap-2">
          <Badge>CSV</Badge>
          <Badge>Excel</Badge>
          <Badge>Executive brief</Badge>
          <Badge>Pivot Explorer</Badge>
          <Badge>Citations</Badge>
          <Badge>Anomalies + explain</Badge>
          <Badge>PDF report</Badge>
        </div>

        <h1 className="mt-7 text-4xl font-semibold tracking-tight text-fg sm:text-6xl">
          Turn any spreadsheet into an{" "}
          <span className="bg-gradient-to-r from-fuchsia-600 to-sky-500 bg-clip-text text-transparent">
            analyst‑grade
          </span>{" "}
          dashboard.
        </h1>

        <p className="mt-5 text-base text-fg-muted sm:text-lg">
          Upload a CSV/Excel file → get charts, anomalies, and a senior‑analyst overview in seconds. Ask questions, run
          pivots, explain spikes, and export a clean PDF.
        </p>

        <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row sm:items-center">
          {primaryCtas.map((c) =>
            c.action === "scroll" ? (
              <Button
                key={c.label}
                onClick={() => document.getElementById("upload")?.scrollIntoView({ behavior: "smooth" })}
                size="lg"
              >
                {c.label}
              </Button>
            ) : (
              <a key={c.label} href={c.href}>
                <Button variant={c.variant ?? "secondary"} size="lg">
                  {c.label}
                </Button>
              </a>
            )
          )}
          <Button variant="secondary" onClick={() => window.open(`${API_BASE_URL}/docs`, "_blank")} size="lg">
            View API docs
          </Button>
        </div>

        {last ? (
          <div className="mt-6 text-sm text-fg-muted">
            Last upload: <span className="text-fg/90">{last.name}</span>{" "}
            {last.rows != null && last.cols != null ? (
              <span className="text-fg/60">
                • {Number(last.rows).toLocaleString()} rows • {Number(last.cols)} cols
              </span>
            ) : null}
          </div>
        ) : (
          <div className="mt-6 text-sm text-fg-muted">
            Try it with any dataset — sales, marketing, finance, product analytics, or research exports.
          </div>
        )}
      </section>

      <section className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MiniCard title="Executive brief" desc="Primary metric, latest vs previous period change, top drivers." />
        <MiniCard title="Pivot Explorer" desc="Group-by + time bucketing + top-N tables/charts with citations." />
        <MiniCard title="Anomalies + explain" desc="Spikes/outliers detected and explained (period vs previous + drivers)." />
        <MiniCard title="Share + PDF" desc="Share link and a clean PDF report with the executive brief." />
      </section>

      <section id="upload" className="mt-12">
        <div className="mx-auto max-w-4xl">
          <UploadDropzone
            busy={busy}
            onFileSelected={onFileSelected}
            hint="Tip: a date column + numeric columns unlocks executive briefs, time-series pivots, and anomaly explanations."
          />
        </div>
      </section>

      <section className="mt-12 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="p-6 sm:p-8 lg:col-span-2">
          <div className="text-sm font-semibold text-fg">Senior analyst workflow (built in)</div>
          <div className="mt-3 text-sm text-fg-muted">
            You don’t just get pretty charts — you get the exact workflow an analyst uses to answer “what changed?” and
            “why?” quickly.
          </div>
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <Step n="01" title="Executive brief" desc="Primary metric, change vs previous period, drivers." />
            <Step n="02" title="Pivot & slice" desc="Group-by, time bucket, top-N, deterministic citations." />
            <Step n="03" title="Explain anomalies" desc="Spot spikes/outliers and generate attribution tables." />
          </div>
        </Card>

        <Card className="p-6 sm:p-8">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-fg">What you can ask</div>
            <Badge>examples</Badge>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Chip>top 10 customers by revenue</Chip>
            <Chip>trend of revenue by month</Chip>
            <Chip>mean order_value</Chip>
            <Chip>explain the spike</Chip>
            <Chip>count by region</Chip>
          </div>
          <div className="mt-4 rounded-2xl border border-card-border bg-bg-soft/40 p-4">
            <div className="text-xs font-medium text-fg-muted">Trust</div>
            <div className="mt-2 text-sm text-fg/90">
              Computed answers and pivots include “how it was computed” citations — great for auditability.
            </div>
          </div>
        </Card>
      </section>

      <section className="mt-12">
        <Card className="p-6 sm:p-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-fg">How it works</div>
              <div className="mt-2 text-sm text-fg-muted">From upload to dashboard to shareable report — end to end.</div>
            </div>
            <Badge>fast</Badge>
          </div>
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-4">
            <Step n="01" title="Upload" desc="Drag/drop CSV/Excel (auth-enabled private history)." />
            <Step n="02" title="Analyze" desc="Profiling, types, correlations, anomalies, chart specs." />
            <Step n="03" title="Explore" desc="Charts, Pivot Explorer, chat, explain spikes." />
            <Step n="04" title="Share" desc="Copy link + export PDF (exec brief included)." />
          </div>
        </Card>
      </section>

      <section className="mt-12">
        <Card className="p-6 sm:p-8">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-fg">Privacy-friendly defaults</div>
            <Badge>health-data mindset</Badge>
          </div>
          <div className="mt-3 text-sm text-fg-muted">
            Uploads run a lightweight PII risk scan and surface warnings in the overview. Datasets are private per user
            (history requires login).
          </div>
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <MiniCard title="PII risk scan" desc="Flags email/phone/name-like columns (best-effort warning)." />
            <MiniCard title="Request IDs + metrics" desc="Each request has a traceable request-id and stored AI event metrics." />
            <MiniCard title="Async processing" desc="Large files can process in background with status polling." />
          </div>
        </Card>
      </section>
    </main>
  );
}

function MiniCard({ title, desc }: { title: string; desc: string }) {
  return (
    <Card className="p-5">
      <div className="text-sm font-semibold text-fg">{title}</div>
      <div className="mt-2 text-sm text-fg-muted">{desc}</div>
    </Card>
  );
}

function Step({ n, title, desc }: { n: string; title: string; desc: string }) {
  return (
    <div className="rounded-2xl border border-card-border bg-bg-soft/50 p-5">
      <div className="text-xs font-medium text-fg-muted">{n}</div>
      <div className="mt-2 text-sm font-semibold text-fg">{title}</div>
      <div className="mt-2 text-sm text-fg-muted">{desc}</div>
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-card-border bg-bg-soft/60 px-3 py-2 text-sm text-fg/90">
      {children}
    </span>
  );
}


