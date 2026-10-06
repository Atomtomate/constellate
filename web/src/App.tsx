import { Route, Routes } from "react-router-dom";

import { useHealth } from "./hooks/useHealth";
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

/**
 * Shows the result of `GET /health` via the typed client. Delegates to `useHealth` so
 * `api/client` stays behind the `hooks/` boundary (web/CLAUDE.md, layer rule 1).
 */
function HealthStatus() {
  const { data, isLoading, isError, error } = useHealth();

  if (isLoading) return <p>Checking API&hellip;</p>;
  if (isError) {
    return <p>API unreachable: {error instanceof Error ? error.message : "Unknown error"}</p>;
  }
  return <p>API status: {data?.status}</p>;
}
