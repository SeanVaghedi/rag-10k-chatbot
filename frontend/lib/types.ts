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
}

export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  sources?: Source[];
  /** True while the assistant message is actively streaming. */
  streaming?: boolean;
  /** True if this message represents an error state. */
  error?: boolean;
}
