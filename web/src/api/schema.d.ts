/**
 * Generated from api/openapi.json by `npm run generate:api-types`. Do not edit by hand.
 * This stub was committed at scaffold time; it is replaced when impl-backend delivers
 * api/openapi.json and step 2 runs `npm run generate:api-types` (impl-director.md,
 * "Hand-offs, concretely: Contract to client").
 *
 * The types here match the shape the real generator produces for the health endpoint and
 * the error envelope components defined by the scaffold (docs/03 Conventions).
 */

export interface paths {
  "/health": {
    get: {
      parameters: Record<string, never>;
      responses: {
        200: {
          headers: { "X-Request-ID"?: string };
          content: { "application/json": { status: string } };
        };
        500: {
          headers: { "X-Request-ID"?: string };
          content: { "application/json": { error: components["schemas"]["ErrorBody"] } };
        };
      };
    };
  };
  "/health/ready": {
    get: {
      parameters: Record<string, never>;
      responses: {
        200: {
          headers: { "X-Request-ID"?: string };
          content: { "application/json": { status: string } };
        };
        500: {
          headers: { "X-Request-ID"?: string };
          content: { "application/json": { error: components["schemas"]["ErrorBody"] } };
        };
      };
    };
  };
}

export interface components {
  schemas: {
    /**
     * The inner `error` object every endpoint returns in the envelope
     * `{"error": {"code", "message", "fields"}}` (docs/03 Conventions, decision 1).
     * `fields` is present only on invalid_request (a malformed body or bad parameter).
     */
    ErrorBody: {
      code: string;
      message: string;
      /** Present only on invalid_request; null or absent otherwise. */
      fields?: components["schemas"]["FieldError"][] | null;
    };
    /** One offending field in an invalid_request error; location names the path through the body. */
    FieldError: {
      location: string[];
      message: string;
    };
  };
  headers: {
    /** Minted per request by the API's ASGI middleware; ties every log line to one client report. */
    "X-Request-ID": string;
  };
}

export type webhooks = Record<string, never>;
