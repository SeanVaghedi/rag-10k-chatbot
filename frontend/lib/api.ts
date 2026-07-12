import type { ConfigInfo, ProgressEvent, Source } from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

/** An HTTP-level API failure, carrying the status code so the UI can map it
 * to friendly copy (429 -> rate-limited, 503 -> unavailable, ...). */
export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Fetch the available configs. The backend wraps the list under a `value` key
 * (`{ value: [...], Count }`), but we also accept a bare array for robustness.
 */
export async function fetchConfigs(signal?: AbortSignal): Promise<ConfigInfo[]> {
  const res = await fetch(`${API_URL}/configs`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to load configs (HTTP ${res.status}).`);
  }
  const data = await res.json();
  const list = Array.isArray(data) ? data : data?.value ?? [];
  return list as ConfigInfo[];
}

export interface StreamHandlers {
  onToken: (text: string) => void;
  onSources: (sources: Source[]) => void;
  /** Real pipeline stage updates emitted before the first token. Optional —
   * older backends never send them, and the UI falls back gracefully. */
  onProgress?: (event: ProgressEvent) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

/**
 * POST to /ask/stream and parse the Server-Sent-Events response.
 *
 * The backend emits framed events:
 *   event: progress -> { stage, label, detail? }  (pipeline stages, pre-token)
 *   event: token   -> { text }
 *   event: sources -> { sources, config }
 *   event: done    -> {}
 *   event: error   -> { message }
 *
 * EventSource only supports GET, so we read the fetch body stream manually.
 */
export async function streamAsk(
  question: string,
  config: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, config }),
    signal,
  });

  if (!res.ok || !res.body) {
    // Carry the backend's message for console logging (e.g. "index not
    // built") plus the status so the UI can choose friendly copy.
    let detail = `Request failed (HTTP ${res.status}).`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flushFrame = (frame: string) => {
    let event = "message";
    let dataStr = "";
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
    }
    if (!dataStr) return;

    let data: any;
    try {
      data = JSON.parse(dataStr);
    } catch {
      return;
    }

    switch (event) {
      case "token":
        handlers.onToken(data.text ?? "");
        break;
      case "progress":
        if (typeof data?.label === "string") {
          handlers.onProgress?.(data as ProgressEvent);
        }
        break;
      case "sources":
        handlers.onSources(data.sources ?? []);
        break;
      case "error":
        handlers.onError?.(data.message ?? "Unknown streaming error.");
        break;
      case "done":
        handlers.onDone?.();
        break;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    // Events are separated by a blank line (\n\n).
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      if (frame.trim()) flushFrame(frame);
    }
  }

  // Flush any trailing frame without a terminating blank line.
  if (buffer.trim()) flushFrame(buffer);
}
