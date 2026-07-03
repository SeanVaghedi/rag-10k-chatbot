"use client";

import { motion } from "framer-motion";
import type { ConfigInfo } from "@/lib/types";

/** Compact display names for the segmented control (full label stays in the
 * tooltip). Presentation-only — the backend `name` is always what's sent. */
const SHORT_LABELS: Record<string, string> = {
  gemini_native: "Gemini",
  openai_native: "OpenAI",
  gemini_llm_openai_embed: "Gemini · OpenAI",
  llama_local: "Llama",
  llama_gemini_embed: "Llama · Gemini",
};

function shortLabel(c: ConfigInfo): string {
  return SHORT_LABELS[c.name] ?? c.label;
}

function StatusDot({ built }: { built: boolean }) {
  return (
    <span className="relative inline-flex h-[7px] w-[7px] shrink-0">
      <span
        className={`absolute inset-0 rounded-full ${
          built ? "bg-good shadow-[0_0_8px_rgba(87,227,137,0.9)]" : "bg-faint"
        }`}
      />
      {built && (
        <span className="absolute inset-0 animate-ping rounded-full bg-good/60" />
      )}
    </span>
  );
}

interface Props {
  configs: ConfigInfo[];
  selected: string;
  onSelect: (name: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

export function ConfigSwitcher({
  configs,
  selected,
  onSelect,
  disabled,
  loading,
}: Props) {
  if (loading) {
    return (
      <div className="glass light-edge flex items-center gap-1 rounded-full p-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-7 w-20 animate-pulse rounded-full bg-white/5"
          />
        ))}
      </div>
    );
  }

  return (
    <div
      role="tablist"
      aria-label="Provider configuration"
      className="glass light-edge no-scrollbar flex max-w-full items-center gap-0.5 overflow-x-auto rounded-full p-1"
    >
      {configs.map((c) => {
        const isSelected = c.name === selected;
        const notBuilt = !c.index_built;
        return (
          <button
            key={c.name}
            role="tab"
            aria-selected={isSelected}
            disabled={disabled || notBuilt}
            onClick={() => !notBuilt && onSelect(c.name)}
            title={notBuilt ? "Index not built yet" : c.label}
            className={[
              "group relative shrink-0 rounded-full px-3.5 py-1.5 transition-colors",
              notBuilt ? "cursor-not-allowed" : "",
              disabled && !isSelected ? "opacity-70" : "",
            ].join(" ")}
          >
            {/* Sliding liquid-glass lens (the signature interaction) */}
            {isSelected && (
              <motion.span
                layoutId="config-lens"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
                className="absolute inset-0 rounded-full bg-gradient-to-br from-accent/30 via-white/10 to-accent2/20 shadow-glow ring-1 ring-inset ring-white/25"
              >
                <span className="absolute inset-x-2 top-0.5 h-1/2 rounded-full bg-white/15 blur-[2px]" />
              </motion.span>
            )}
            <span className="relative z-10 flex items-center gap-2">
              <StatusDot built={c.index_built} />
              <span
                className={[
                  "whitespace-nowrap text-[13px] font-medium transition-colors",
                  isSelected
                    ? "text-white"
                    : notBuilt
                      ? "text-faint"
                      : "text-muted group-hover:text-ink",
                ].join(" ")}
              >
                {shortLabel(c)}
              </span>
            </span>

            {/* Tooltip for unbuilt indexes */}
            {notBuilt && (
              <span className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 -translate-x-1/2 whitespace-nowrap rounded-lg bg-black/85 px-2.5 py-1 text-[11px] text-ink opacity-0 shadow-lg ring-1 ring-white/10 transition-opacity duration-150 group-hover:opacity-100">
                Index not built yet
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
