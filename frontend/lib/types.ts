export interface ConfigInfo {
  name: string;
  label: string;
  index_built: boolean;
}

export interface Source {
  company: string | null;
  year: number | null;
  page: number | null;
  source_filename: string | null;
  /** Raw retrieved chunk text; used to highlight the passage in the PDF. */
  chunk_text?: string | null;
}

/** A real pipeline stage reported by the backend while an answer streams
 * (embedding, searching, reranking, reading, composing, …). */
export interface ProgressEvent {
  stage: string;
  label: string;
  detail?: Record<string, unknown>;
}

export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  sources?: Source[];
  /** For assistant messages: pipeline progress steps received while this
   * answer was generated. Shown live during thinking, then kept as a
   * collapsible "Thought process" summary. */
  thinking?: ProgressEvent[];
  /** For assistant messages: the user question this answer responds to
   * (frontend-only; shown as context in the sources panel). */
  question?: string;
  /** True while the assistant message is actively streaming. */
  streaming?: boolean;
  /** True if this message represents an error state. */
  error?: boolean;
}
