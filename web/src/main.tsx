import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import "./index.css";

/**
 * The application root: QueryClient, BrowserRouter, App. Sign-in wiring (`RequireSession`,
 * session hooks, the 401→reset-["me"] query-invalidation rule) arrives with M1's sign-in
 * screen and is not in scope for the scaffold (impl-director.md "Not in scope").
 */
const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
