"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Button, Card, Badge } from "@/components/ui";
import { requestLoginCode, setToken, verifyLoginCode } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get("next") || "/";
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [stage, setStage] = useState<"email" | "code">("email");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const canRequest = useMemo(() => email.trim().includes("@"), [email]);
  const canVerify = useMemo(() => email.trim().includes("@") && code.trim().length >= 4, [email, code]);

  async function onRequest() {
    if (!canRequest || busy) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await requestLoginCode(email.trim());
      setDevCode(res.dev_code ?? null);
      setStage("code");
    } catch (e: any) {
      setErr(e?.message ?? "Failed to request code.");
    } finally {
      setBusy(false);
    }
  }

  async function onVerify() {
    if (!canVerify || busy) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await verifyLoginCode(email.trim(), code.trim());
      setToken(res.access_token);
      router.replace(next);
    } catch (e: any) {
      setErr(e?.message ?? "Failed to verify code.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl px-4 py-14">
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xl font-semibold text-fg">Sign in</div>
            <div className="mt-1 text-sm text-fg-muted">Passwordless login (email code). This unlocks private history.</div>
          </div>
          <Badge>beta</Badge>
        </div>

        <div className="mt-6 space-y-3">
          <label className="block text-xs font-medium text-fg-muted">Email</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="h-11 w-full rounded-xl border border-card-border bg-card/50 px-4 text-sm text-fg placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/40"
          />

          {stage === "code" ? (
            <>
              <label className="mt-4 block text-xs font-medium text-fg-muted">Code</label>
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="6-digit code"
                className="h-11 w-full rounded-xl border border-card-border bg-card/50 px-4 text-sm text-fg placeholder:text-fg-muted focus:outline-none focus:ring-2 focus:ring-accent/40"
              />
            </>
          ) : null}

          {devCode ? (
            <div className="rounded-xl border border-card-border bg-bg-soft/40 p-3 text-sm text-fg/90">
              Dev code: <span className="font-mono">{devCode}</span>
              <div className="mt-1 text-xs text-fg-muted">In production, this would be emailed.</div>
            </div>
          ) : null}

          {err ? <div className="text-sm text-red-600">{err}</div> : null}

          <div className="mt-4 flex gap-2">
            {stage === "email" ? (
              <Button onClick={onRequest} disabled={!canRequest || busy}>
                {busy ? "Sending…" : "Send code"}
              </Button>
            ) : (
              <Button onClick={onVerify} disabled={!canVerify || busy}>
                {busy ? "Signing in…" : "Sign in"}
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={() => {
                setStage("email");
                setCode("");
                setDevCode(null);
              }}
            >
              Reset
            </Button>
          </div>

          <div className="mt-3 text-xs text-fg-muted">
            After signing in you can upload, see your private history, and delete datasets.
          </div>
        </div>
      </Card>
    </main>
  );
}

