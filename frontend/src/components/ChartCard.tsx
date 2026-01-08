"use client";

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, Badge } from "./ui";
import { formatNumber } from "@/lib/format";

function tooltipStyle() {
  return {
    contentStyle: {
      background: "rgba(255,255,255,0.98)",
      border: "1px solid rgba(15,23,42,0.12)",
      borderRadius: 14,
      color: "rgba(15,23,42,0.92)",
    },
    labelStyle: { color: "rgba(15,23,42,0.62)" },
  } as const;
}

export function ChartCard({ chart }: { chart: any }) {
  const type = chart?.type ?? "unknown";
  const title = chart?.title ?? "Chart";
  const meta: string[] = [];
  if (type === "line") {
    if (chart?.time_grain) meta.push(String(chart.time_grain));
    if (chart?.agg && chart.agg !== "count") meta.push(String(chart.agg));
    if (chart?.y === "__count__" || chart?.agg === "count") meta.push("count");
  }

  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-sm font-semibold text-fg leading-snug">{title}</div>
          <div className="mt-1 text-xs text-fg-muted">
            {type.toUpperCase()}
            {meta.length ? ` • ${meta.join(" • ")}` : ""}
          </div>
        </div>
        <Badge>{chart?.x ? `x: ${chart.x}` : "auto"}</Badge>
      </div>

      <div className="mt-4 h-[320px] w-full">
        {type === "line" ? <LineView chart={chart} /> : null}
        {type === "bar" ? <BarView chart={chart} /> : null}
        {type === "hist" ? <HistView chart={chart} /> : null}
        {type === "scatter" ? <ScatterView chart={chart} /> : null}
        {type === "table" ? <TableView chart={chart} /> : null}
        {type === "unknown" ? <UnknownView chart={chart} /> : null}
      </div>
    </Card>
  );
}

function LineView({ chart }: { chart: any }) {
  const data = Array.isArray(chart?.data) ? chart.data : [];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="rgba(15,23,42,0.08)" vertical={false} />
        <XAxis
          dataKey="x"
          tick={{ fill: "rgba(15,23,42,0.60)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(15,23,42,0.12)" }}
          minTickGap={24}
        />
        <YAxis
          tick={{ fill: "rgba(15,23,42,0.60)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(15,23,42,0.12)" }}
          width={56}
          tickFormatter={(v) => formatNumber(v)}
        />
        <Tooltip {...tooltipStyle()} />
        <Line type="monotone" dataKey="y" stroke="rgb(124, 58, 237)" strokeWidth={2.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function BarView({ chart }: { chart: any }) {
  const data = Array.isArray(chart?.data) ? chart.data : [];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="rgba(15,23,42,0.08)" vertical={false} />
        <XAxis
          dataKey="x"
          tick={{ fill: "rgba(15,23,42,0.60)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(15,23,42,0.12)" }}
          interval={0}
          angle={-20}
          height={52}
        />
        <YAxis
          tick={{ fill: "rgba(15,23,42,0.60)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(15,23,42,0.12)" }}
          width={56}
          tickFormatter={(v) => formatNumber(v)}
        />
        <Tooltip {...tooltipStyle()} />
        <Bar dataKey="y" fill="rgba(124, 58, 237, 0.80)" radius={[10, 10, 4, 4]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function HistView({ chart }: { chart: any }) {
  const raw = Array.isArray(chart?.data) ? chart.data : [];
  const data = raw.map((d: any) => ({ x: d.bin ?? d.x ?? "", y: d.count ?? d.y ?? 0 }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="rgba(15,23,42,0.08)" vertical={false} />
        <XAxis
          dataKey="x"
          tick={{ fill: "rgba(15,23,42,0.55)", fontSize: 10 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(15,23,42,0.12)" }}
          interval="preserveStartEnd"
          minTickGap={16}
        />
        <YAxis
          tick={{ fill: "rgba(15,23,42,0.60)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(15,23,42,0.12)" }}
          width={56}
        />
        <Tooltip {...tooltipStyle()} />
        <Bar dataKey="y" fill="rgba(2, 132, 199, 0.75)" radius={[10, 10, 4, 4]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function ScatterView({ chart }: { chart: any }) {
  const data = Array.isArray(chart?.data) ? chart.data : [];
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ScatterChart margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="rgba(15,23,42,0.08)" />
        <XAxis
          type="number"
          dataKey="x"
          tick={{ fill: "rgba(15,23,42,0.60)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(15,23,42,0.12)" }}
        />
        <YAxis
          type="number"
          dataKey="y"
          tick={{ fill: "rgba(15,23,42,0.60)", fontSize: 12 }}
          tickLine={false}
          axisLine={{ stroke: "rgba(15,23,42,0.12)" }}
          width={56}
          tickFormatter={(v) => formatNumber(v)}
        />
        <Tooltip {...tooltipStyle()} cursor={{ stroke: "rgba(124,58,237,0.25)" }} />
        <Scatter data={data} fill="rgba(124, 58, 237, 0.45)" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function TableView({ chart }: { chart: any }) {
  const rows = Array.isArray(chart?.data) ? chart.data : [];
  const cols = rows.length ? Object.keys(rows[0]) : [];
  return (
    <div className="h-full overflow-auto rounded-xl border border-card-border bg-bg-soft/40">
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
    </div>
  );
}

function UnknownView({ chart }: { chart: any }) {
  return (
    <div className="h-full rounded-xl border border-card-border bg-bg-soft/40 p-4 text-sm text-fg-muted overflow-auto">
      <div className="text-fg font-semibold">Unsupported chart type</div>
      <pre className="mt-3 text-xs whitespace-pre-wrap">{JSON.stringify(chart, null, 2)}</pre>
    </div>
  );
}


