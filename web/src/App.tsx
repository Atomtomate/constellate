import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";

import { NotFound } from "./routes/NotFound";

/**
 * The routed shell. The API answers only under `/api`, so this app owns every other path.
 *
 * At scaffold time the only routes are the health status at `/` and the `NotFound`
 * fallback. Product routes (timeline, totals) arrive with M1 screens, each in its own PR.
 */
export function App() {
  return (
    <Routes>
      {/* Product routes (timeline, totals) arrive with M1 */}
      <Route index element={<HealthStatus />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; status: string }
  | { kind: "error"; message: string };

/**
 * Calls GET /health and displays the result. Uses a plain fetch rather than the typed
 * api/ client, because api/client may only be imported by hooks/ and api/ (web layer
 * rule 1). A hook in hooks/ wrapping the typed client arrives with M1.
 */
function HealthStatus() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) {
          return res.json().then((body: unknown) => {
            const msg =
              typeof body === "object" &&
              body !== null &&
              "error" in body &&
              typeof (body as { error: unknown }).error === "object" &&
              (body as { error: { message?: unknown } }).error !== null
                ? String((body as { error: { message?: string } }).error.message ?? res.statusText)
                : res.statusText;
            if (!cancelled) setHealth({ kind: "error", message: msg });
          });
        }
        return res.json().then((data: { status: string }) => {
          if (!cancelled) setHealth({ kind: "ok", status: data.status });
        });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setHealth({
            kind: "error",
            message: err instanceof Error ? err.message : "Fetch failed",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (health.kind === "loading") return <p>Checking API&hellip;</p>;
  if (health.kind === "error") return <p>API unreachable: {health.message}</p>;
  return <p>API status: {health.status}</p>;
}
