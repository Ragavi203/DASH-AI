"use client";

import { Button } from "./ui";

export function TopNav() {
  return (
    <div className="sticky top-0 z-40 border-b border-card-border bg-bg/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
        <a href="/" className="group flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-accent/10 ring-1 ring-accent/20 shadow-sm grid place-items-center">
            <span className="text-fg font-bold">D</span>
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-fg group-hover:text-fg">DashAI</div>
            <div className="text-[12px] text-fg-muted">CSV → Instant dashboard</div>
          </div>
        </a>

        <div className="flex items-center gap-2">
          <a className="text-sm text-fg-muted hover:text-fg transition px-2 py-2" href="/history">
            History
          </a>
          <a
            className="hidden sm:inline text-sm text-fg-muted hover:text-fg transition"
            href="https://github.com/"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <a href="#upload">
            <Button variant="secondary">Upload</Button>
          </a>
        </div>
      </div>
    </div>
  );
}


