import type { Metadata } from "next";
import "@/styles/globals.css";
import { TopNav } from "@/components/TopNav";

export const metadata: Metadata = {
  title: "DashAI — CSV → Instant Dashboard",
  description: "Upload any CSV/Excel and get charts, insights, anomalies, and a shareable dashboard in seconds.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-fg">
        <div className="bg-grid min-h-screen">
          <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(1100px_circle_at_20%_0%,rgba(168,85,247,0.12),transparent_55%),radial-gradient(900px_circle_at_85%_20%,rgba(56,189,248,0.10),transparent_55%)]" />
          <TopNav />
          {children}
          <footer className="mx-auto max-w-7xl px-4 py-12 text-xs text-fg-muted">
            Built with Next.js + FastAPI • Upload stays on your machine in this demo unless you deploy storage.
          </footer>
        </div>
      </body>
    </html>
  );
}


