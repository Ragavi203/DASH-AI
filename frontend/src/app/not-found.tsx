import { Card, Button } from "@/components/ui";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-14">
      <Card className="p-6">
        <div className="text-xl font-semibold text-fg">Page not found</div>
        <div className="mt-2 text-sm text-fg-muted">That link doesn’t exist (or it was removed).</div>
        <div className="mt-6">
          <a href="/">
            <Button variant="secondary">Back to upload</Button>
          </a>
        </div>
      </Card>
    </main>
  );
}


