"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { UploadDropzone } from "@/components/UploadDropzone";
import { Badge, Button, Card } from "@/components/ui";
import { API_BASE_URL, uploadDataset } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<{ name: string; rows?: number; cols?: number } | null>(null);

  async function onFileSelected(file: File) {
    setBusy(true);
    try {
      const res = await uploadDataset(file);
      const shape = res?.analysis?.profile?.shape ?? {};
      setLast({ name: file.name, rows: shape.rows, cols: shape.cols });
      router.push(`/d/${res.dataset_id}?share=${encodeURIComponent(res.share_id)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-14 sm:py-20">
      <section className="mx-auto max-w-3xl text-center">
        <div className="flex flex-wrap justify-center gap-2">
          <Badge>CSV</Badge>
          <Badge>Excel</Badge>
          <Badge>Auto charts</Badge>
          <Badge>Anomalies</Badge>
          <Badge>Q&A</Badge>
          <Badge>PDF</Badge>
        </div>

        <h1 className="mt-6 text-4xl font-semibold tracking-tight text-fg sm:text-6xl">
          Instant dashboards for{" "}
          <span className="bg-gradient-to-r from-fuchsia-600 to-sky-500 bg-clip-text text-transparent">
            any spreadsheet
          </span>
          .
        </h1>

        <p className="mt-5 text-base text-fg-muted sm:text-lg">
          Upload a CSV/Excel file and get a clean, interactive dashboard in seconds—charts, insights, and anomalies
          included. Ask questions in plain English.
        </p>

        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button
            onClick={() => document.getElementById("upload")?.scrollIntoView({ behavior: "smooth" })}
            size="lg"
          >
            Upload a file
          </Button>
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
        ) : null}
      </section>

      <section className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MiniCard title="Auto charts" desc="Line, bar, histogram, scatter—picked from your columns." />
        <MiniCard title="Insights" desc="Readable takeaways, data quality flags, correlations." />
        <MiniCard title="Anomalies" desc="Spikes & outliers highlighted with explainable rules." />
        <MiniCard title="Share + PDF" desc="Send a link or export a quick report." />
      </section>

      <section id="upload" className="mt-12">
        <div className="mx-auto max-w-4xl">
          <UploadDropzone
            busy={busy}
            onFileSelected={onFileSelected}
            hint="Tip: a date column + numeric columns makes charts and anomaly detection shine."
          />
        </div>
      </section>

      <section className="mt-12">
        <Card className="p-6 sm:p-8">
          <div className="text-sm font-semibold text-fg">How it works</div>
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <Step n="01" title="Upload" desc="Drop a CSV/Excel. Paste works too." />
            <Step n="02" title="Analyze" desc="Column types, correlations, anomalies, chart specs." />
            <Step n="03" title="Explore" desc="Charts + chat + share link + PDF export." />
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


