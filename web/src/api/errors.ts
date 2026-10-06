import type { components } from "./schema";

/** The one error shape every endpoint returns (docs/03 Conventions, decision 1). */
export type ErrorBody = components["schemas"]["ErrorBody"];

/** Typed against the generated contract so a server-side rename fails `tsc`. */
const REQUEST_ID_HEADER = "X-Request-ID" satisfies keyof components["headers"];

/**
 * What `ApiError` needs to construct itself -- `ErrorBody`, but with `code` widened from
 * the contract's closed union to a plain `string`. A real `ErrorBody` still satisfies it;
 * what does not is `toErrorBody`'s synthetic `unexpected_response`, for a response that
 * was never a valid `ErrorBody` in the first place, so typing it as one would be exactly
 * the lie this file exists to avoid.
 *
 * `requestId` is optional so a test can build one without a `Response`; `toErrorBody`
 * always provides it.
 */
type ApiErrorInput = {
  code: string;
  message: string;
  fields?: ErrorBody["fields"];
  requestId?: string | null;
};

/**
 * Thrown by every query function in place of a bare fetch failure, so a screen's error
 * state has the envelope's `code` and `message` to switch on rather than a generic
 * "request failed". Callers match on `code`'s value and must not hard-code an exhaustive
 * list -- `code` is a closed enum in the contract, but this class also stands in for a
 * response that was never a valid envelope at all (`toErrorBody`).
 *
 * `requestId` carries the `X-Request-ID` response header when present, so a user can
 * copy it to the owner for log correlation. It is null when the header is absent -- a
 * proxy error page (Vite's, Caddy's) never sets it -- or when the error is constructed
 * without a `Response` (form helpers, tests).
 */
export class ApiError extends Error {
  readonly code: string;
  readonly fields: components["schemas"]["FieldError"][] | null;
  readonly requestId: string | null;

  constructor(body: ApiErrorInput) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.fields = body.fields ?? null;
    this.requestId = body.requestId ?? null;
  }
}

/**
 * The shape every `openapi-fetch` call is typed as returning -- `error` is only ever
 * `undefined` when `data` is present, per the generated `paths` types -- but the type is a
 * promise about what the *contract* says, not about what actually came back over the wire,
 * so this file treats `error`/`data` as `unknown` until `toErrorBody` has looked.
 */
type FetchResult<T> = {
  data?: T;
  error?: unknown;
  response: Response;
};

/**
 * True when `raw` actually has the one error shape every endpoint promises --
 * `{error: {code, message}}`. It usually does, but a broken proxy's error page is
 * `text/plain` -- `openapi-fetch` hands back whatever the body was (a string it could not
 * parse as JSON, or JSON of some other shape entirely), typed as the envelope only because
 * that is what the contract says a response should be.
 */
function isErrorEnvelope(raw: unknown): raw is { error: ErrorBody } {
  if (typeof raw !== "object" || raw === null || !("error" in raw)) {
    return false;
  }
  const body = (raw as { error: unknown }).error;
  return (
    typeof body === "object" &&
    body !== null &&
    typeof (body as { code?: unknown }).code === "string" &&
    typeof (body as { message?: unknown }).message === "string"
  );
}

/**
 * `raw` coerced to an `ErrorBody` -- the envelope's own `error` when `raw` is actually
 * shaped like one (`isErrorEnvelope`), or a generic body built from the response's own
 * status when it is not, so a caller never has to guard against a malformed body itself.
 * `unexpected_response` is not a code the API issues; it exists so `describeError` and a
 * screen's `switch` still have something to match against instead of a `TypeError`.
 */
function toErrorBody(raw: unknown, response: Response): ApiErrorInput {
  const requestId = response.headers.get(REQUEST_ID_HEADER);
  if (isErrorEnvelope(raw)) {
    return { ...raw.error, requestId };
  }
  return {
    code: "unexpected_response",
    message: response.statusText || `Unexpected response (${response.status})`,
    fields: null,
    requestId,
  };
}

/**
 * Unwraps an `openapi-fetch` result. Every screen's query function ends with this rather
 * than reading `data`/`error` itself, so a 401 with no session surfaces the same way a 404
 * or a 500 would: as a thrown `ApiError` that `@tanstack/react-query` turns into query
 * `error` state. Checks `response.ok` rather than truthy `error` alone -- `openapi-fetch`
 * can hand back `error: undefined` on a non-2xx with an empty body (a 204-shaped error,
 * a HEAD), which a bare `if (result.error)` would misread as success.
 */
export function unwrap<T>(result: FetchResult<T>): T {
  if (!result.response.ok || result.error !== undefined) {
    throw new ApiError(toErrorBody(result.error, result.response));
  }
  if (result.data === undefined) {
    throw new Error("the server answered success with no body");
  }
  return result.data;
}

/**
 * `unwrap`, except one error `code` is folded into `null` instead of thrown -- for a
 * caller where that code is a legitimate answer ("there is no session"), not a failure to
 * report as one.
 */
export function unwrapOrNull<T>(result: FetchResult<T>, code: string): T | null {
  if (!result.response.ok || result.error !== undefined) {
    const body = toErrorBody(result.error, result.response);
    if (body.code === code) {
      return null;
    }
    throw new ApiError(body);
  }
  if (result.data === undefined) {
    throw new Error("the server answered success with no body");
  }
  return result.data;
}

/** `unwrap` for an endpoint whose success response carries no body (a 204) -- nothing to
 * return, only the chance to throw. */
export function unwrapNoContent(result: { error?: unknown; response: Response }): void {
  if (!result.response.ok || result.error !== undefined) {
    throw new ApiError(toErrorBody(result.error, result.response));
  }
}

/**
 * A short, user-facing line for the error codes a caller can actually hit mid-use.
 * Everything else falls through to the server's own `message` rather than a
 * hand-maintained code list -- the API already wrote it.
 */
export function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.code) {
      case "unauthenticated":
        return "Signed out -- sign in again to see this.";
      case "forbidden":
        return "Not visible to this account.";
      case "not_found":
        return "That isn't here (any more).";
      default:
        return err.message;
    }
  }
  return "Something went wrong loading this.";
}

/**
 * A `422`'s `fields` array turned into one line naming what failed -- the one place in
 * the client that reads `FieldError.location` (the contract's own "which field") rather
 * than discarding it. `errors.ts` is `ErrorBody`'s owner, so this lives beside
 * `describeError` rather than in whichever screen happens to be the first to render a
 * validation failure.
 *
 * Pydantic's own "Value error, " prefix -- raised from a custom validator, not a
 * length/type check -- is stripped as library internals nobody asked to see; the rest of
 * `message` is always the server's own text, never a replacement for it.
 */
export function describeFieldErrors(fields: components["schemas"]["FieldError"][]): string {
  return fields
    .map((field) => {
      const name = field.location.at(-1);
      const message = field.message.replace(/^Value error,\s*/, "");
      return name ? `${name}: ${message}` : message;
    })
    .join(" ");
}

/**
 * A form's error line: one screen-owned sentence for the codes that screen can name,
 * and the server's own words for everything else.
 *
 * `lines` is keyed by `ApiError.code`, deliberately a plain `string` rather than the
 * contract's closed union: this helper must also survive `toErrorBody`'s synthetic
 * `unexpected_response`. A code the caller does not name is not an omission -- it falls
 * through to the server's text, which is the correct default and the reason a screen names
 * only what it improves on.
 *
 * `describeError` is reached only by something that is not an `ApiError` at all: a
 * network failure, or a thrown non-error. An `ApiError` never gets its data-screen copy
 * ("Not visible to this account."), which is a non sequitur on a form.
 */
export function describeFormError(error: unknown, lines: Record<string, string>): string {
  if (error instanceof ApiError) {
    const named = lines[error.code];
    if (named !== undefined) {
      return named;
    }
    if (error.fields && error.fields.length > 0) {
      return describeFieldErrors(error.fields);
    }
    return error.message;
  }
  return describeError(error);
}
