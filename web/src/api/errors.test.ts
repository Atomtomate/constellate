import { describe, it, expect } from "vitest";
import { ApiError, unwrap } from "./errors.ts";

/**
 * `ApiError.requestId` is read from the `X-Request-ID` response header through
 * `toErrorBody`; `unwrap` is the entry point that exercises the full path. The header is
 * the only externally-observable surface (the internal `toErrorBody` is not exported), so
 * these cases test via `unwrap` rather than directly.
 */
describe("ApiError.requestId", () => {
  function failWith(headers: Record<string, string> = {}): ApiError {
    const response = new Response(
      JSON.stringify({ error: { code: "not_found", message: "not found" } }),
      { status: 404, headers: { "Content-Type": "application/json", ...headers } },
    );
    try {
      unwrap({
        data: undefined,
        error: { error: { code: "not_found", message: "not found" } },
        response,
      });
    } catch (e) {
      if (e instanceof ApiError) return e;
    }
    throw new Error("unwrap did not throw");
  }

  it("carries the request id when the header is present", () => {
    const err = failWith({ "X-Request-ID": "req-abc-123" });
    expect(err.requestId).toBe("req-abc-123");
  });

  it("is null when the header is absent", () => {
    const err = failWith();
    expect(err.requestId).toBeNull();
  });
});

