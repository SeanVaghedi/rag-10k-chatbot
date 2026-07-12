/** Friendly, user-facing error copy. Raw payloads (provider JSON, stack
 * traces, status objects) are logged to the console by callers — never shown
 * in the chat. */

/** Matches the copy of the existing backend-unreachable banner. */
export const BACKEND_UNREACHABLE_MESSAGE =
  "Can't reach the backend. Start the API on port 8000, then retry.";

export const RATE_LIMIT_MESSAGE =
  "The model is temporarily rate-limited. Please try again in a moment.";

export const UNAVAILABLE_MESSAGE =
  "The model service is briefly unavailable. Please retry.";

export const GENERIC_ERROR_MESSAGE =
  "Something went wrong generating that answer. Please try again.";

// Provider/raw-text signatures, used when no HTTP status is available (e.g.
// mid-stream SSE error events carry the provider exception as text).
const RATE_LIMIT_RE =
  /\b429\b|rate.?limit|resource[_ ]exhausted|quota|too many requests/i;
const UNAVAILABLE_RE =
  /\b50[234]\b|unavailable|overloaded|deadline exceeded|timed? ?out/i;
const UNREACHABLE_RE = /failed to fetch|networkerror|load failed|fetch failed/i;

/**
 * Map a raw error (HTTP status and/or provider text) to friendly chat copy.
 * Status wins when present; otherwise the raw text is pattern-matched.
 */
export function friendlyErrorMessage(raw: string, status?: number): string {
  if (status === 429) return RATE_LIMIT_MESSAGE;
  if (status === 502 || status === 503 || status === 504) {
    return UNAVAILABLE_MESSAGE;
  }

  const text = raw ?? "";
  if (RATE_LIMIT_RE.test(text)) return RATE_LIMIT_MESSAGE;
  if (UNAVAILABLE_RE.test(text)) return UNAVAILABLE_MESSAGE;
  if (UNREACHABLE_RE.test(text)) return BACKEND_UNREACHABLE_MESSAGE;
  return GENERIC_ERROR_MESSAGE;
}
