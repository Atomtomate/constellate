import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { ApiError } from "./api/errors";
import { App } from "./App";
import "./index.css";

/**
 * The query client is set up with one retry rule: do not retry on `ApiError` -- the API
 * already answered, and asking again cannot change it. Sign-in wiring (resetting `["me"]`
 * on a 401, `RequireSession`, session hooks) arrives with M1's sign-in screen and is not
 * in scope for the scaffold (impl-director.md "Not in scope").
 *
 * The session cookie name will be updated from whatever the backend names it when the
 * backend spec says; on the web side the name lives only in the sign-in hook's docstring.
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // An ApiError means the API answered with an envelope -- a 401, a 404, a broken
      // rule. Asking again cannot change it, so retrying only leaves the screen on
      // "Loading..." for the library's default backoff before landing on the same answer.
      retry: (failures, error) => !(error instanceof ApiError) && failures < 2,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
