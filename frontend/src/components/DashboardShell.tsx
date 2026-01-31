"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Badge, Button, Card } from "./ui";
import { ChartCard } from "./ChartCard";
import { formatNumber } from "@/lib/format";
import { chat, explainAnomaly, getChatHistory, pivot, reportPdfUrl } from "@/lib/api";

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <Card className="p-4">
      <div className="text-xs text-fg-muted">{label}</div>
      <div className="mt-1 text-lg font-semibold text-fg">{value}</div>
    </Card>
  );
}

export function DashboardShell({
  datasetId,
  shareId,
  analysis,
  showShare,
}: {
  datasetId: string;
  shareId: string;
  analysis: any;
  showShare?: boolean;
}) {
  const [tab, setTab] = useState<"overview" | "charts" | "data" | "chat">("overview");
  const [copied, setCopied] = useState(false);

  const shape = analysis?.profile?.shape ?? {};
  const rows = shape?.rows ?? null;
  const cols = shape?.cols ?? null;
  const insights = Array.isArray(analysis?.insights) ? analysis.insights : [];
  const anomalies = Array.isArray(analysis?.anomalies) ? analysis.anomalies : [];
  const charts = Array.isArray(analysis?.charts) ? analysis.charts : [];
  const preview = Array.isArray(analysis?.preview) ? analysis.preview : [];
  const overview = analysis?.overview ?? null;
  const execBrief = overview?.executive_brief ?? null;
  const dataDict = overview?.data_dictionary ?? null;

  const chartSections = useMemo(() => {
    const bySection: Record<string, any[]> = {};
    for (const c of charts) {
      const sec = String(c?.section ?? "");
      const key = sec || (c?.type === "line" ? "Trends" : c?.type === "bar" ? "Breakdowns" : c?.type === "hist" ? "Distributions" : c?.type === "scatter" ? "Relationships" : c?.type === "table" ? "Tables" : "Other");
      bySection[key] = bySection[key] || [];
      bySection[key].push(c);
    }
    const order = ["Recommended", "Trends", "Breakdowns", "Distributions", "Relationships", "Tables", "Other"];
    const desc: Record<string, string> = {
      Recommended: "The most useful views for this dataset.",
      Trends: "How metrics evolve over time.",
      Breakdowns: "What drives totals across categories.",
      Distributions: "How values are spread.",
      Relationships: "How two metrics move together.",
      Tables: "Raw previews and summaries.",
      Other: "",
    };
    return order
      .filter((k) => (bySection[k] || []).length)
      .map((k) => ({ key: k.toLowerCase(), title: k, desc: desc[k] ?? "", charts: bySection[k] }));
  }, [charts]);

  const correlations = Array.isArray(analysis?.profile?.strong_correlations)
    ? analysis.profile.strong_correlations
    : [];
  const privacy = overview?.privacy ?? null;

  const [explainBusy, setExplainBusy] = useState<number | null>(null);
  const [explainResult, setExplainResult] = useState<any | null>(null);

  // Pivot Explorer (analyst workflow)
  const types = analysis?.types ?? {};
  const allCols = Array.isArray(overview?.columns) ? overview.columns : Object.keys(types || {});
  const numericCols = allCols.filter((c: string) => String(types?.[c]) === "numeric");
  const dtCols = allCols.filter((c: string) => String(types?.[c]) === "datetime");
  const catCols = allCols.filter((c: string) => String(types?.[c]) === "categorical");

  const [pivotBusy, setPivotBusy] = useState(false);
  const [pivotRes, setPivotRes] = useState<any | null>(null);
  const [pivotGroupBy, setPivotGroupBy] = useState<string>(catCols[0] || "");
  const [pivotMetric, setPivotMetric] = useState<string>(numericCols[0] || "");
  const [pivotAgg, setPivotAgg] = useState<"sum" | "mean" | "count">("sum");
  const [pivotDate, setPivotDate] = useState<string>(dtCols[0] || "");
  const [pivotGrain, setPivotGrain] = useState<"day" | "week" | "month">("month");
  const [pivotTopN, setPivotTopN] = useState<number>(12);
  const [pivotMode, setPivotMode] = useState<"categorical" | "timeseries">("categorical");

  const shareUrl = useMemo(() => {
    if (typeof window === "undefined") return "";
    return `${window.location.origin}/s/${shareId}`;
  }, [shareId]);

  async function copyShare() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // ignore
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:py-12">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="text-2xl font-semibold tracking-tight text-fg">Dashboard</div>
            <Badge>auto</Badge>
            {anomalies.length ? <Badge tone="warn">{anomalies.length} anomalies</Badge> : <Badge tone="good">clean</Badge>}
          </div>
          <div className="mt-1 text-sm text-fg-muted">
            Dataset <span className="text-fg/80 font-mono">{datasetId.slice(0, 8)}…</span> •{" "}
            {rows != null ? `${Number(rows).toLocaleString()} rows` : "—"} • {cols != null ? `${cols} cols` : "—"}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" onClick={() => window.open(reportPdfUrl(datasetId), "_blank")}>
            Export PDF
          </Button>
          {showShare ? (
            <Button variant="secondary" onClick={copyShare} title={shareUrl || ""}>
              {copied ? "Copied!" : "Copy share link"}
            </Button>
          ) : null}
          <a href="/" className="text-sm text-fg-muted hover:text-fg transition px-2 py-2">
            Upload another →
          </a>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        <Tab label="Overview" active={tab === "overview"} onClick={() => setTab("overview")} />
        <Tab label={`Charts (${charts.length})`} active={tab === "charts"} onClick={() => setTab("charts")} />
        <Tab label="Data preview" active={tab === "data"} onClick={() => setTab("data")} />
        <Tab label="Chat" active={tab === "chat"} onClick={() => setTab("chat")} />
      </div>

      {tab === "overview" ? (
        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-1">
            {(overview?.kpis ? overview.kpis : []).slice(0, 6).map((k: any, idx: number) => (
              <Stat key={idx} label={String(k.label)} value={typeof k.value === "number" ? formatNumber(k.value) : String(k.value)} />
            ))}
            {!overview?.kpis ? (
              <>
                <Stat label="Rows" value={rows != null ? formatNumber(rows) : "—"} />
                <Stat label="Columns" value={cols != null ? formatNumber(cols) : "—"} />
                <Stat label="Charts" value={formatNumber(charts.length)} />
              </>
            ) : null}
          </div>

          <Card className="lg:col-span-2 p-5">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-fg">Key insights</div>
              <Badge>auto-written</Badge>
            </div>
            <div className="mt-4 space-y-3">
              {overview?.highlights?.length ? (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {overview.highlights.slice(0, 4).map((h: any, idx: number) => (
                    <div key={idx} className="rounded-xl border border-card-border bg-bg-soft/40 p-3">
                      <div className="text-xs text-fg-muted">{String(h.type ?? "highlight").toUpperCase()}</div>
                      <div className="mt-1 text-sm text-fg/90">{String(h.text ?? "")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
              {insights.length ? (
                insights.map((i: any, idx: number) => (
                  <div key={idx} className="rounded-xl border border-card-border bg-bg-soft/40 p-3">
                    <div className="text-xs text-fg-muted">{String(i?.type ?? "insight").toUpperCase()}</div>
                    <div className="mt-1 text-sm text-fg/90">{String(i?.text ?? "")}</div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-fg-muted">No insights generated.</div>
              )}
            </div>
          </Card>

          {execBrief?.bullets?.length ? (
            <Card className="lg:col-span-3 p-5">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-fg">Executive brief</div>
                <Badge>analyst</Badge>
              </div>
              <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="lg:col-span-1">
                  <ul className="space-y-2 text-sm text-fg/90">
                    {execBrief.bullets.slice(0, 6).map((b: string, idx: number) => (
                      <li key={idx} className="flex gap-2">
                        <span className="mt-1 h-1.5 w-1.5 rounded-full bg-accent/70" />
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="lg:col-span-2 space-y-4">
                  {execBrief.trend_chart ? <ChartCard chart={execBrief.trend_chart} /> : null}
                  {execBrief.drivers?.rows?.length ? (
                    <div className="rounded-2xl border border-card-border bg-bg-soft/40 p-4">
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-semibold text-fg">Drivers (latest vs previous)</div>
                        <Badge>{String(execBrief.drivers.dimension)}</Badge>
                      </div>
                      <div className="mt-3 overflow-auto rounded-xl border border-card-border bg-bg/70">
                        <table className="min-w-full text-left text-xs">
                          <thead className="bg-bg/90 border-b border-card-border">
                            <tr>
                              <th className="px-3 py-2 font-medium text-fg-muted">Segment</th>
                              <th className="px-3 py-2 font-medium text-fg-muted">Current</th>
                              <th className="px-3 py-2 font-medium text-fg-muted">Previous</th>
                              <th className="px-3 py-2 font-medium text-fg-muted">Δ</th>
                            </tr>
                          </thead>
                          <tbody>
                            {execBrief.drivers.rows.slice(0, 8).map((r: any, i: number) => (
                              <tr key={i} className="border-b border-card-border/60 last:border-b-0">
                                <td className="px-3 py-2 text-fg/90">{String(r.segment)}</td>
                                <td className="px-3 py-2 text-fg/90">{formatNumber(Number(r.current))}</td>
                                <td className="px-3 py-2 text-fg/90">{formatNumber(Number(r.previous))}</td>
                                <td className="px-3 py-2">
                                  <Badge tone={Number(r.delta) >= 0 ? "good" : "warn"}>{formatNumber(Number(r.delta))}</Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="mt-2 text-xs text-fg-muted">
                        Tip: click “Explain” on a spike anomaly for period attribution + citations.
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </Card>
          ) : null}

          <Card className="lg:col-span-3 p-5">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-fg">Pivot Explorer</div>
              <Badge>analyst</Badge>
            </div>
            <div className="mt-3 text-sm text-fg-muted">
              Build a deterministic slice (group-by, aggregate, time bucket) — like a senior analyst would, with citations.
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-6">
              <div className="md:col-span-1">
                <div className="text-xs font-medium text-fg-muted">Mode</div>
                <select
                  value={pivotMode}
                  onChange={(e) => setPivotMode(e.target.value as any)}
                  className="mt-1 h-10 w-full rounded-xl border border-card-border bg-card/50 px-3 text-sm text-fg"
                >
                  <option value="categorical">Category</option>
                  <option value="timeseries">Time series</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <div className="text-xs font-medium text-fg-muted">{pivotMode === "timeseries" ? "Date column" : "Group by"}</div>
                <select
                  value={pivotMode === "timeseries" ? pivotDate : pivotGroupBy}
                  onChange={(e) => (pivotMode === "timeseries" ? setPivotDate(e.target.value) : setPivotGroupBy(e.target.value))}
                  className="mt-1 h-10 w-full rounded-xl border border-card-border bg-card/50 px-3 text-sm text-fg"
                >
                  {(pivotMode === "timeseries" ? dtCols : catCols).map((c: string) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <div className="text-xs font-medium text-fg-muted">Metric</div>
                <select
                  value={pivotAgg === "count" ? "__rows__" : pivotMetric}
                  onChange={(e) => setPivotMetric(e.target.value)}
                  disabled={pivotAgg === "count"}
                  className="mt-1 h-10 w-full rounded-xl border border-card-border bg-card/50 px-3 text-sm text-fg disabled:opacity-60"
                >
                  {numericCols.map((c: string) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-1">
                <div className="text-xs font-medium text-fg-muted">Agg</div>
                <select
                  value={pivotAgg}
                  onChange={(e) => setPivotAgg(e.target.value as any)}
                  className="mt-1 h-10 w-full rounded-xl border border-card-border bg-card/50 px-3 text-sm text-fg"
                >
                  <option value="sum">sum</option>
                  <option value="mean">mean</option>
                  <option value="count">count</option>
                </select>
              </div>

              {pivotMode === "timeseries" ? (
                <div className="md:col-span-2">
                  <div className="text-xs font-medium text-fg-muted">Grain</div>
                  <select
                    value={pivotGrain}
                    onChange={(e) => setPivotGrain(e.target.value as any)}
                    className="mt-1 h-10 w-full rounded-xl border border-card-border bg-card/50 px-3 text-sm text-fg"
                  >
                    <option value="day">day</option>
                    <option value="week">week</option>
                    <option value="month">month</option>
                  </select>
                </div>
              ) : (
                <div className="md:col-span-2">
                  <div className="text-xs font-medium text-fg-muted">Top N</div>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={pivotTopN}
                    onChange={(e) => setPivotTopN(Number(e.target.value || 12))}
                    className="mt-1 h-10 w-full rounded-xl border border-card-border bg-card/50 px-3 text-sm text-fg"
                  />
                </div>
              )}

              <div className="md:col-span-6 flex items-center gap-2">
                <Button
                  onClick={async () => {
                    setPivotBusy(true);
                    setPivotRes(null);
                    try {
                      const payload =
                        pivotMode === "timeseries"
                          ? {
                              date_col: pivotDate || null,
                              time_grain: pivotGrain,
                              metric: pivotAgg === "count" ? null : pivotMetric || null,
                              agg: pivotAgg,
                              group_by: [],
                              chart_type: "line",
                              top_n: 50,
                            }
                          : {
                              group_by: pivotGroupBy ? [pivotGroupBy] : [],
                              metric: pivotAgg === "count" ? null : pivotMetric || null,
                              agg: pivotAgg,
                              top_n: pivotTopN,
                              chart_type: "bar",
                            };
                      const res = await pivot(datasetId, payload);
                      setPivotRes(res);
                    } catch (e: any) {
                      setPivotRes({ type: "text", text: e?.message ?? "Pivot failed." });
                    } finally {
                      setPivotBusy(false);
                    }
                  }}
                  disabled={pivotBusy}
                >
                  {pivotBusy ? "Running…" : "Run pivot"}
                </Button>
                <span className="text-xs text-fg-muted">
                  This is deterministic (no LLM). Great to demo “trustworthy analytics + reproducibility”.
                </span>
              </div>
            </div>

            {pivotRes ? (
              <div className="mt-4 space-y-4">
                <div className="text-sm text-fg/90">{String(pivotRes.text ?? "")}</div>
                {pivotRes.chart ? <ChartCard chart={pivotRes.chart} /> : null}
                {pivotRes.table ? (
                  <details className="rounded-xl border border-card-border bg-bg/60 px-3 py-2">
                    <summary className="cursor-pointer text-xs font-medium text-fg-muted">View table</summary>
                    <div className="mt-2 overflow-auto rounded-xl border border-card-border bg-bg/70">
                      <table className="min-w-full text-left text-xs">
                        <thead className="bg-bg/90 border-b border-card-border">
                          <tr>
                            {(pivotRes.table.columns || []).map((c: string) => (
                              <th key={c} className="px-3 py-2 font-medium text-fg-muted">
                                {c}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {(pivotRes.table.rows || []).slice(0, 20).map((r: any, i: number) => (
                            <tr key={i} className="border-b border-card-border/60 last:border-b-0">
                              {(pivotRes.table.columns || []).map((c: string) => (
                                <td key={c} className="px-3 py-2 text-fg/90">
                                  {String(r?.[c] ?? "")}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                ) : null}
                {pivotRes.citations ? (
                  <details className="rounded-xl border border-card-border bg-bg/60 px-3 py-2">
                    <summary className="cursor-pointer text-xs font-medium text-fg-muted">Citations</summary>
                    <pre className="mt-2 text-[11px] text-fg-muted whitespace-pre-wrap">
                      {JSON.stringify(pivotRes.citations, null, 2)}
                    </pre>
                  </details>
                ) : null}
              </div>
            ) : null}
          </Card>

          {dataDict?.columns?.length ? (
            <Card className="lg:col-span-3 p-5">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-fg">Data dictionary</div>
                <Badge>{dataDict.columns.length} columns</Badge>
              </div>
              <details className="mt-4 rounded-2xl border border-card-border bg-bg-soft/40 px-4 py-3">
                <summary className="cursor-pointer text-sm text-fg-muted">Show inferred schema, missing %, and notes</summary>
                <div className="mt-3 overflow-auto rounded-xl border border-card-border bg-bg/70">
                  <table className="min-w-full text-left text-xs">
                    <thead className="bg-bg/90 border-b border-card-border">
                      <tr>
                        <th className="px-3 py-2 font-medium text-fg-muted">Column</th>
                        <th className="px-3 py-2 font-medium text-fg-muted">Type</th>
                        <th className="px-3 py-2 font-medium text-fg-muted">Missing %</th>
                        <th className="px-3 py-2 font-medium text-fg-muted">Examples</th>
                        <th className="px-3 py-2 font-medium text-fg-muted">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dataDict.columns.slice(0, 30).map((c: any, idx: number) => (
                        <tr key={idx} className="border-b border-card-border/60 last:border-b-0">
                          <td className="px-3 py-2 text-fg/90">{String(c.column)}</td>
                          <td className="px-3 py-2">
                            <Badge>{String(c.type)}</Badge>
                          </td>
                          <td className="px-3 py-2 text-fg/90">{String(c.missing_pct ?? "—")}</td>
                          <td className="px-3 py-2 text-fg/90">{Array.isArray(c.examples) ? c.examples.join(", ") : ""}</td>
                          <td className="px-3 py-2 text-fg/90">{Array.isArray(c.notes) ? c.notes.join(", ") : ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-2 text-xs text-fg-muted">Showing first 30 columns to keep the UI snappy.</div>
              </details>
            </Card>
          ) : null}

          {privacy?.risk && privacy.risk !== "low" ? (
            <Card className="lg:col-span-3 p-5">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-fg">Privacy / PII risk</div>
                <Badge tone={privacy.risk === "high" ? "bad" : "warn"}>{String(privacy.risk).toUpperCase()}</Badge>
              </div>
              <div className="mt-3 text-sm text-fg-muted">
                Potential sensitive columns detected. For health data, treat uploads as PHI/PII and restrict sharing.
              </div>
              <div className="mt-4 space-y-2">
                {(privacy.findings || []).slice(0, 6).map((f: any, idx: number) => (
                  <div key={idx} className="rounded-xl border border-card-border bg-bg-soft/40 p-3">
                    <div className="text-sm font-medium text-fg">{String(f.column)}</div>
                    <div className="mt-1 text-xs text-fg-muted">
                      Signals: {Array.isArray(f.signals) ? f.signals.join(", ") : "—"}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ) : null}

          {overview?.suggested_questions?.length ? (
            <Card className="lg:col-span-3 p-5">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-fg">Suggested questions</div>
                <Badge>chat</Badge>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {overview.suggested_questions.slice(0, 8).map((q: string, idx: number) => (
                  <span key={idx} className="rounded-full border border-card-border bg-bg-soft/60 px-3 py-2 text-sm text-fg/90">
                    {q}
                  </span>
                ))}
              </div>
              <div className="mt-3 text-xs text-fg-muted">Copy/paste any of these into the Chat tab.</div>
            </Card>
          ) : null}

          <Card className="lg:col-span-3 p-5">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-fg">Signals</div>
              <div className="flex gap-2">
                {correlations.length ? <Badge>{correlations.length} correlations</Badge> : <Badge tone="neutral">—</Badge>}
                {anomalies.length ? <Badge tone="warn">{anomalies.length} anomalies</Badge> : <Badge tone="good">0 anomalies</Badge>}
              </div>
            </div>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="rounded-xl border border-card-border bg-bg-soft/40 p-4">
                <div className="text-xs text-fg-muted">Top correlations</div>
                <div className="mt-2 space-y-2">
                  {correlations.slice(0, 5).map((c: any, idx: number) => (
                    <div key={idx} className="flex items-center justify-between gap-3">
                      <div className="text-sm text-fg/90 truncate">
                        {c.a} ↔ {c.b}
                      </div>
                      <Badge>{Number(c.corr).toFixed(2)}</Badge>
                    </div>
                  ))}
                  {!correlations.length ? <div className="text-sm text-fg-muted">No strong correlations found.</div> : null}
                </div>
              </div>

              <div className="rounded-xl border border-card-border bg-bg-soft/40 p-4">
                <div className="text-xs text-fg-muted">Top anomalies</div>
                <div className="mt-2 space-y-2">
                  {anomalies.slice(0, 6).map((a: any, idx: number) => (
                    <div key={idx} className="flex items-start justify-between gap-3">
                      <div className="text-sm text-fg/90">
                        {a.type === "spike" ? (
                          <>
                            Spike in <span className="font-medium">{a.y_col}</span> at{" "}
                            <span className="font-mono text-fg/80">{String(a.x).slice(0, 19)}</span>
                          </>
                        ) : (
                          <>
                            Outlier in <span className="font-medium">{a.col}</span>:{" "}
                            <span className="font-mono text-fg/80">{formatNumber(a.value)}</span>
                          </>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {a.type === "spike" ? (
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={explainBusy === idx}
                            onClick={async () => {
                              setExplainBusy(idx);
                              setExplainResult(null);
                              try {
                                const res = await explainAnomaly(datasetId, idx);
                                setExplainResult({ idx, res });
                              } catch (e: any) {
                                setExplainResult({ idx, res: { type: "text", text: e?.message ?? "Explain failed." } });
                              } finally {
                                setExplainBusy(null);
                              }
                            }}
                          >
                            {explainBusy === idx ? "Explaining…" : "Explain"}
                          </Button>
                        ) : null}
                        <Badge tone="warn">{a.score ? Number(a.score).toFixed(2) : "!"}</Badge>
                      </div>
                    </div>
                  ))}
                  {!anomalies.length ? <div className="text-sm text-fg-muted">No anomalies detected.</div> : null}
                </div>
              </div>
            </div>
          </Card>

          {explainResult?.res ? (
            <Card className="lg:col-span-3 p-5">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-fg">Spike explanation</div>
                <Badge>computed</Badge>
              </div>
              <div className="mt-3 text-sm text-fg/90">{String(explainResult.res.text ?? "")}</div>
              {explainResult.res.chart ? (
                <div className="mt-4">
                  <ChartCard chart={explainResult.res.chart} />
                </div>
              ) : null}
              {explainResult.res.table ? (
                <div className="mt-4 overflow-auto rounded-xl border border-card-border bg-bg/70">
                  <table className="min-w-full text-left text-xs">
                    <thead className="bg-bg/90 border-b border-card-border">
                      <tr>
                        {(explainResult.res.table.columns || []).map((c: string) => (
                          <th key={c} className="px-3 py-2 font-medium text-fg-muted">
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(explainResult.res.table.rows || []).map((r: any, i: number) => (
                        <tr key={i} className="border-b border-card-border/60 last:border-b-0">
                          {(explainResult.res.table.columns || []).map((c: string) => (
                            <td key={c} className="px-3 py-2 text-fg/90">
                              {String(r?.[c] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
              {explainResult.res.citations ? (
                <details className="mt-4 rounded-xl border border-card-border bg-bg/60 px-3 py-2">
                  <summary className="cursor-pointer text-xs font-medium text-fg-muted">How it was computed</summary>
                  <pre className="mt-2 text-[11px] text-fg-muted whitespace-pre-wrap">
                    {JSON.stringify(explainResult.res.citations, null, 2)}
                  </pre>
                </details>
              ) : null}
            </Card>
          ) : null}
        </div>
      ) : null}

      {tab === "charts" ? (
        <div className="mt-8 space-y-8">
          {chartSections.map((sec) => (
            <div key={sec.key}>
              <div className="flex items-end justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-fg">{sec.title}</div>
                  {sec.desc ? <div className="mt-1 text-sm text-fg-muted">{sec.desc}</div> : null}
                </div>
                <Badge>{sec.charts.length}</Badge>
              </div>

              <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-2">
                {sec.charts.map((c: any, idx: number) => (
                  <ChartCard key={`${sec.key}:${c?.title ?? idx}`} chart={c} />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {tab === "data" ? (
        <Card className="mt-6 p-5">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-fg">Preview</div>
            <Badge>{preview.length} rows</Badge>
          </div>
          <div className="mt-4 overflow-auto rounded-xl border border-card-border bg-bg-soft/40">
            <DataTable rows={preview} />
          </div>
        </Card>
      ) : null}

      {tab === "chat" ? (
        <ChatPanel datasetId={datasetId} />
      ) : null}
    </div>
  );
}

function Tab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={[
        "rounded-xl px-4 py-2 text-sm transition border",
        active
          ? "bg-accent/10 border-accent/25 text-fg"
          : "bg-card/40 border-card-border text-fg-muted hover:text-fg hover:bg-card/60",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function DataTable({ rows }: { rows: any[] }) {
  const cols = rows.length ? Object.keys(rows[0]) : [];
  return (
    <table className="min-w-full text-left text-xs">
      <thead className="sticky top-0 bg-bg/80 backdrop-blur border-b border-card-border">
        <tr>
          {cols.map((c) => (
            <th key={c} className="px-3 py-2 font-medium text-fg-muted">
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r: any, idx: number) => (
          <tr key={idx} className="border-b border-card-border/60 hover:bg-card/60">
            {cols.map((c) => (
              <td key={c} className="px-3 py-2 text-fg/90">
                {String(r[c] ?? "")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ChatPanel({ datasetId }: { datasetId: string }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<
    Array<{ role: "user" | "ai"; text: string; table?: any; chart?: any; kind?: string; citations?: any }>
  >([
    {
      role: "ai",
      text: "Ask things like: “top 10 customers by revenue”, “average order_value”, or “what caused the spike in March?”",
    },
  ]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await getChatHistory(datasetId);
        const hist = Array.isArray(res?.messages) ? res.messages : [];
        if (cancelled) return;
        if (!hist.length) return;
        const mapped = hist.map((m: any) => ({
          role: m.role === "user" ? ("user" as const) : ("ai" as const),
          text: String(m.text ?? ""),
          kind: String(m.type ?? "text"),
          table: m.table,
          chart: m.chart,
          citations: m.citations,
        }));
        setMessages(mapped);
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  async function send() {
    const question = q.trim();
    if (!question || busy) return;
    setQ("");
    setMessages((m) => [...m, { role: "user", text: question }]);
    setBusy(true);
    try {
      const res = await chat(datasetId, question);
      const answer = res?.answer ?? {};
      const answerText = answer?.text ?? "No answer.";
      setMessages((m) => [
        ...m,
        {
          role: "ai",
          text: String(answerText),
          kind: String(answer?.type ?? "text"),
          table: answer?.table,
          chart: answer?.chart,
          citations: answer?.citations,
        },
      ]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "ai", text: e?.message ?? "Chat failed." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="mt-6 p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-fg">Chat with your data</div>
        <Badge>beta</Badge>
      </div>

      <div className="mt-4 h-[420px] overflow-auto rounded-2xl border border-card-border bg-bg-soft/40 p-4">
        <div className="space-y-3">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={[
                "max-w-[92%] rounded-2xl px-4 py-3 text-sm border",
                m.role === "user"
                  ? "ml-auto bg-accent/10 border-accent/25 text-fg"
                  : "mr-auto bg-card/60 border-card-border text-fg/90",
              ].join(" ")}
            >
              <div className="text-[11px] uppercase tracking-wide text-fg-muted">{m.role === "user" ? "You" : "AI"}</div>
              <div className="mt-1 whitespace-pre-wrap">{m.text}</div>
              {m.role === "ai" && m.kind === "chart" && m.chart ? (
                <div className="mt-3">
                  <ChartCard chart={m.chart} />
                </div>
              ) : null}
              {m.role === "ai" && m.kind === "table" && m.table ? (
                <div className="mt-3">
                  <InlineTable table={m.table} />
                </div>
              ) : null}
              {m.role === "ai" && m.citations ? (
                <details className="mt-3 rounded-xl border border-card-border bg-bg/60 px-3 py-2">
                  <summary className="cursor-pointer text-xs font-medium text-fg-muted">How it was computed</summary>
                  <pre className="mt-2 text-[11px] text-fg-muted whitespace-pre-wrap">
                    {JSON.stringify(m.citations, null, 2)}
                  </pre>
                </details>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void send();
          }}
          placeholder="Ask a question…"
          className="h-11 flex-1 rounded-xl border border-card-border bg-card/50 px-4 text-sm text-fg placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/40"
        />
        <Button onClick={send} disabled={busy}>
          {busy ? "Thinking…" : "Send"}
        </Button>
      </div>
    </Card>
  );
}

function InlineTable({ table }: { table: any }) {
  const rows = Array.isArray(table?.rows) ? table.rows : [];
  const colsFromSchema = Array.isArray(table?.columns) ? table.columns : null;
  const cols = colsFromSchema ?? (rows.length ? Object.keys(rows[0]) : []);
  if (!rows.length) return null;
  return (
    <div className="overflow-auto rounded-xl border border-card-border bg-bg/70">
      <table className="min-w-full text-left text-xs">
        <thead className="bg-bg/90 border-b border-card-border">
          <tr>
            {cols.slice(0, 8).map((c: string) => (
              <th key={c} className="px-3 py-2 font-medium text-fg-muted">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((r: any, i: number) => (
            <tr key={i} className="border-b border-card-border/60 last:border-b-0">
              {cols.slice(0, 8).map((c: string) => (
                <td key={c} className="px-3 py-2 text-fg/90">
                  {String(r?.[c] ?? r?.value ?? r?.name ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


