/**
 * Hook for `GET /health`. Lives in `hooks/` so `routes/` and top-level components can
 * call the typed API client through react-query without breaching the layer rule that
 * restricts `api/client` imports to `hooks/` and `api/` (web/CLAUDE.md, layer rule 1).
 */

import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { unwrap } from "../api/errors";
import { queryKeys } from "../api/queryKeys";
import type { components } from "../api/schema";

type HealthOkResponse = components["schemas"]["HealthOkResponse"];

/**
 * Calls `GET /health` and returns the react-query result. `data.status` is `"ok"` when the
 * process is up; `error` is an `ApiError` when the API answered with the envelope, and the
 * fetch's own `Error` when nothing answered at all. No auth is involved -- the endpoint is
 * public and the scaffold uses it as a smoke test.
 */
export function useHealth() {
  return useQuery<HealthOkResponse>({
    queryKey: queryKeys.health,
    queryFn: async (): Promise<HealthOkResponse> => unwrap(await api.GET("/health")),
  });
}
