import { describe, it, expect } from "vitest";
import { ApiError, describeFormError, unwrap } from "./errors.ts";

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

/**
 * `describeFormError` is the shared error line for forms. The helper is pure, so it
 * needs no jsdom and no new devDependency.
 */
describe("describeFormError", () => {
  const named = { forbidden: "Incorrect current password." };

  it("prefers the screen's own line for a code it names", () => {
    const error = new ApiError({ code: "forbidden", message: "incorrect password" });
    expect(describeFormError(error, named)).toBe("Incorrect current password.");
  });

  it("renders the server's message for a code the screen does not name", () => {
    const error = new ApiError({ code: "not_found", message: "the item has gone" });
    expect(describeFormError(error, named)).toBe("the item has gone");
  });

  it("names the fields of a 422 that carries them", () => {
    const error = new ApiError({
      code: "invalid_request",
      message: "The request could not be processed",
      fields: [{ location: ["body", "title"], message: "String should have at least 1 character" }],
    });
    expect(describeFormError(error, named)).toBe(
      "title: String should have at least 1 character",
    );
  });

  it("prefers a named line over fields, so the screen's wording wins where it has one", () => {
    const error = new ApiError({
      code: "forbidden",
      message: "incorrect password",
      fields: [{ location: ["body", "current_password"], message: "nope" }],
    });
    expect(describeFormError(error, named)).toBe("Incorrect current password.");
  });

  it("falls back to describeError only for something that is not an ApiError", () => {
    expect(describeFormError(new TypeError("Failed to fetch"), named)).toBe(
      "Something went wrong loading this.",
    );
  });
});
