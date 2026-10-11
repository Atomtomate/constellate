/**
 * Query keys shared across modules. A key lives here as soon as a second module needs
 * it -- at that point a rename at one end silently breaks the other, and centralising the
 * constant makes the mismatch a compile error rather than a missed refresh.
 *
 * Decision 4 (impl-director.md): this file exists from the scaffold so the layer test can
 * walk it, which is why `health` is here although one hook reads it. Product keys (session,
 * timeline, totals) arrive with M1 screens.
 */

/** Shared query keys, one property per endpoint family. */
export const queryKeys = {
  /** `GET /health` -- the process liveness probe shown on the scaffold home screen. */
  health: ["health"] as const,
} as const;
