"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { Badge, Button, Card, Kbd } from "./ui";

type Props = {
  onFileSelected: (file: File) => Promise<void> | void;
  busy?: boolean;
  hint?: string;
};

const ACCEPT = [".csv", ".tsv", ".xlsx", ".xls"];

export function UploadDropzone({ onFileSelected, busy, hint }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const acceptAttr = useMemo(() => ACCEPT.join(","), []);

  const pick = useCallback(() => inputRef.current?.click(), []);

  const validate = useCallback((f: File) => {
    const name = f.name.toLowerCase();
    const ok = ACCEPT.some((ext) => name.endsWith(ext));
    if (!ok) throw new Error("Please upload a CSV/TSV or Excel file.");
    if (f.size > 50 * 1024 * 1024) throw new Error("File too large (limit 50MB for this demo).");
  }, []);

  const handleFile = useCallback(
    async (file: File) => {
      try {
        setError(null);
        validate(file);
        await onFileSelected(file);
      } catch (e: any) {
        setError(e?.message ?? "Upload failed.");
      }
    },
    [onFileSelected, validate]
  );

  useEffect(() => {
    function onPaste(e: ClipboardEvent) {
      if (busy) return;
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const it of items) {
        if (it.kind === "file") {
          const f = it.getAsFile();
          if (f) {
            void handleFile(f);
            return;
          }
        }
      }
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [busy, handleFile]);

  return (
    <Card className={clsx("p-5 sm:p-6", dragging && "ring-2 ring-accent/40")}>
      <div
        className={clsx(
          "relative rounded-2xl border border-card-border bg-bg-soft/60 p-6 sm:p-8 transition",
          "hover:border-card-border/70"
        )}
        onDragEnter={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragging(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragging(false);
          const f = e.dataTransfer?.files?.[0];
          if (f) void handleFile(f);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={acceptAttr}
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleFile(f);
            e.currentTarget.value = "";
          }}
        />

        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="h-12 w-12 rounded-2xl bg-accent/15 ring-1 ring-accent/20 shadow-glow grid place-items-center">
              <span className="text-accent text-lg">↑</span>
            </div>
            <div>
              <div className="text-base font-semibold text-fg">Drop your file here</div>
              <div className="text-sm text-fg-muted">
                CSV / TSV / Excel. We auto-detect charts, anomalies, and insights.
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge>Instant charts</Badge>
                <Badge>Insights</Badge>
                <Badge tone="warn">Anomalies</Badge>
                <Badge>Share link</Badge>
                <Badge>PDF export</Badge>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={pick} disabled={busy}>
              {busy ? "Analyzing…" : "Upload file"}
            </Button>
            <div className="hidden md:flex items-center gap-2 text-xs text-fg-muted">
              <span>Paste:</span>
              <Kbd>⌘</Kbd> <Kbd>V</Kbd>
            </div>
          </div>
        </div>

        {hint ? <div className="mt-4 text-xs text-fg-muted">{hint}</div> : null}
        {error ? <div className="mt-4 text-sm text-bad">{error}</div> : null}
      </div>
    </Card>
  );
}


