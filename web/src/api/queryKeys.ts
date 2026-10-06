/**
 * Query keys shared across modules. A key lives here as soon as a second module needs
 * it -- at that point a rename at one end silently breaks the other, and centralising the
 * constant makes the mismatch a compile error rather than a missed refresh.
 *
 * Decision 4 (impl-director.md): this file exists from the scaffold so the layer test can
 * walk it. Product keys (session, timeline, totals) arrive with M1 screens.
 */

/** The process-liveness cache key. Used by the health-status component in App.tsx. */
export const HEALTH_QUERY_KEY = ["health"] as const;
