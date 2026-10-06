import createClient from "openapi-fetch";

import type { paths } from "./schema";

/**
 * The one HTTP client every screen goes through, typed against the generated schema so a
 * call site cannot ask for a path, method or body the API does not have. `credentials:
 * "include"` sends the session cookie on every request -- M1's sign-in is when the
 * browser first has one to send.
 *
 * The API and this app share one origin in every environment; the API answers under `/api`
 * and the website owns every other path (docs/03-architecture.md Conventions, "One
 * origin"). `openapi-fetch` does not read the spec's `servers` entry, so this constant is
 * the only place the base URL exists on the web side -- there is nothing else to keep in
 * step with the contract here.
 */
export const api = createClient<paths>({
  baseUrl: "/api",
  credentials: "include",
});
