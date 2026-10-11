import { useHealth } from "../hooks/useHealth";

/**
 * Index route: shows the result of `GET /health` via the typed client. Delegates to
 * `useHealth` so `api/client` stays behind the `hooks/` boundary (web/CLAUDE.md, layer
 * rule 1).
 */
export function Health() {
  const { data, isLoading, isError, error } = useHealth();

  if (isLoading) return <p>Checking API&hellip;</p>;
  if (isError) {
    return <p>API unreachable: {error instanceof Error ? error.message : "Unknown error"}</p>;
  }
  return <p>API status: {data?.status}</p>;
}
