import { Route, Routes } from "react-router-dom";

import { Health } from "./routes/Health";
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
      <Route index element={<Health />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
