"use client";

import React from "react";
import clsx from "clsx";

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost" | "danger";
    size?: "sm" | "md" | "lg";
  }
) {
  const { className, variant = "primary", size = "md", ...rest } = props;
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition shadow-sm focus:outline-none focus:ring-2 focus:ring-accent/25 disabled:opacity-50 disabled:cursor-not-allowed";
  const variants: Record<string, string> = {
    primary: "bg-accent text-white hover:brightness-105",
    secondary: "bg-card border border-card-border text-fg hover:bg-bg-soft",
    ghost: "bg-transparent text-fg-muted hover:text-fg hover:bg-bg-soft",
    danger: "bg-bad text-white hover:brightness-105",
  };
  const sizes: Record<string, string> = {
    sm: "h-9 px-3 text-sm",
    md: "h-10 px-4 text-sm",
    lg: "h-11 px-5 text-base",
  };
  return <button className={clsx(base, variants[variant], sizes[size], className)} {...rest} />;
}

export function Card(props: React.HTMLAttributes<HTMLDivElement>) {
  const { className, ...rest } = props;
  return (
    <div
      className={clsx(
        "rounded-2xl border border-card-border bg-card/85 backdrop-blur shadow-sm",
        className
      )}
      {...rest}
    />
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-bg-soft text-fg-muted border-card-border",
    good: "bg-good/12 text-good border-good/20",
    warn: "bg-warn/12 text-warn border-warn/20",
    bad: "bg-bad/12 text-bad border-bad/20",
  };
  return (
    <span className={clsx("inline-flex items-center rounded-full border px-2.5 py-1 text-xs", tones[tone])}>
      {children}
    </span>
  );
}

export function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded-lg border border-card-border bg-bg-soft px-2 py-1 text-[11px] text-fg-muted">
      {children}
    </kbd>
  );
}


