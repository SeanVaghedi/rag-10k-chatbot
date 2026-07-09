"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";

/**
 * "Model & Configs" — an informational panel documenting the production
 * configuration (gemini_native) and the evaluation that selected it.
 *
 * Everything here is static content: a record of our analysis, not a live
 * control surface. There is deliberately no model switcher and no API call —
 * the product runs one configuration, and this panel shows the receipts.
 */

const RUNNING_CONFIG: { label: string; value: string }[] = [
  { label: "LLM", value: "Google Gemini 2.5 Pro" },
  { label: "Embeddings", value: "gemini-embedding-001" },
  { label: "Vector store", value: "FAISS (local, similarity search)" },
  { label: "Chunk size / overlap", value: "1000 / 150 tokens" },
  { label: "Retrieval depth (k)", value: "5" },
  {
    label: "Corpus",
    value: "Alphabet, Amazon, Microsoft 10-K filings (FY2025)",
  },
];

interface EvalRow {
  config: string;
  llm: string;
  embeddings: string;
  chunk: string;
  number: string;
  boundary: string;
  keyFacts: string;
  selected?: boolean;
}

/** Gold-set eval results across the five candidate configurations. */
const EVAL_ROWS: EvalRow[] = [
  {
    config: "gemini_native",
    llm: "Gemini 2.5 Pro",
    embeddings: "Gemini",
    chunk: "1000",
    number: "100%",
    boundary: "100%",
    keyFacts: "80%",
    selected: true,
  },
  {
    config: "gemini_nomic_embed",
    llm: "Gemini 2.5 Pro",
    embeddings: "nomic (local)",
    chunk: "1000",
    number: "100%",
    boundary: "100%",
    keyFacts: "35%",
  },
  {
    config: "gemini_native_cs500",
    llm: "Gemini 2.5 Pro",
    embeddings: "Gemini",
    chunk: "500",
    number: "100%",
    boundary: "100%",
    keyFacts: "53%",
  },
  {
    config: "llama_local",
    llm: "Llama 3.1 8B",
    embeddings: "nomic (local)",
    chunk: "1000",
    number: "80%",
    boundary: "100%",
    keyFacts: "35%",
  },
  {
    config: "llama_gemini_embed",
    llm: "Llama 3.1 8B",
    embeddings: "Gemini",
    chunk: "1000",
    number: "80%",
    boundary: "100%",
    keyFacts: "53%",
  },
];

/** Key-facts hit-rate by retrieval depth (k sweep on gemini_native). */
const K_SWEEP = [
  { k: 3, keyFacts: 43, selected: false },
  { k: 5, keyFacts: 70, selected: true },
  { k: 8, keyFacts: 70, selected: false },
];

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="font-display text-[12px] font-semibold uppercase tracking-[0.18em] text-muted">
      {children}
    </h3>
  );
}

/** The header trigger. The pulsing dot signals a live production config. */
export function ModelConfigsButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="glass light-edge sheen relative flex h-10 shrink-0 items-center gap-2.5 overflow-hidden rounded-xl px-3.5 text-[13px] font-medium text-muted transition-colors hover:text-ink"
    >
      <span className="relative inline-flex h-[7px] w-[7px]" aria-hidden>
        <span className="absolute inset-0 rounded-full bg-good shadow-[0_0_8px_rgba(87,227,137,0.9)]" />
        <span className="absolute inset-0 animate-ping rounded-full bg-good/60" />
      </span>
      Model &amp; Configs
    </button>
  );
}

export function ModelConfigPanel({ onClose }: { onClose: () => void }) {
  // Close on Escape (same convention as the PDF viewer).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <motion.div
      className="fixed inset-0 z-[60] flex items-center justify-center p-3 sm:p-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      role="dialog"
      aria-modal="true"
      aria-label="Model and configuration"
    >
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-md"
        onClick={onClose}
      />

      <motion.div
        className="glass-panel light-edge relative flex max-h-full w-full max-w-2xl flex-col overflow-hidden rounded-2xl"
        initial={{ opacity: 0, y: 22, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 14, scale: 0.98 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-white/[0.06] px-5 py-4">
          <div className="min-w-0">
            <h2 className="font-display text-[17px] font-bold tracking-tight">
              <span className="text-aurora">Model &amp; Configuration</span>
            </h2>
            <p className="mt-0.5 text-[12.5px] text-muted">
              The shipped configuration, and the evaluation that picked it.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-white/10 hover:text-ink"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M6 6l12 12M18 6L6 18"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="min-h-0 flex-1 space-y-7 overflow-y-auto px-5 py-5">
          {/* A — Running configuration */}
          <section aria-label="Running configuration">
            <div className="flex items-center gap-2.5">
              <Eyebrow>Running configuration</Eyebrow>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-good/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-good ring-1 ring-inset ring-good/25">
                <span className="h-1.5 w-1.5 rounded-full bg-good shadow-[0_0_6px_rgba(87,227,137,0.9)]" />
                live
              </span>
            </div>
            <dl className="mt-3 divide-y divide-white/[0.05] rounded-xl bg-white/[0.025] px-4 ring-1 ring-inset ring-white/[0.06]">
              {RUNNING_CONFIG.map((row) => (
                <div
                  key={row.label}
                  className="grid gap-0.5 py-2.5 sm:grid-cols-[176px_1fr] sm:gap-3"
                >
                  <dt className="text-[12px] leading-5 text-muted">
                    {row.label}
                  </dt>
                  <dd className="font-mono text-[12.5px] leading-5 text-ink">
                    {row.value}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          {/* B — Why this configuration */}
          <section aria-label="Why this configuration">
            <Eyebrow>Why this configuration</Eyebrow>
            <div className="mt-3 overflow-x-auto rounded-xl ring-1 ring-inset ring-white/[0.06]">
              <table className="w-full min-w-[600px] border-collapse text-left">
                <thead>
                  <tr className="bg-white/[0.03]">
                    {[
                      "Config",
                      "LLM",
                      "Embeddings",
                      "Chunk",
                      "Number acc",
                      "Boundary acc",
                      "Key-facts",
                    ].map((h) => (
                      <th
                        key={h}
                        scope="col"
                        className="whitespace-nowrap px-3 py-2 font-mono text-[10.5px] font-medium uppercase tracking-wider text-muted"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="text-[12.5px]">
                  {EVAL_ROWS.map((row) => (
                    <tr
                      key={row.config}
                      className={
                        row.selected
                          ? "bg-gradient-to-r from-accent/[0.14] to-accent2/[0.07]"
                          : "border-t border-white/[0.04]"
                      }
                    >
                      <td className="whitespace-nowrap px-3 py-2.5">
                        <span className="flex items-center gap-2">
                          <span
                            className={`font-mono ${
                              row.selected
                                ? "font-semibold text-white"
                                : "text-ink/80"
                            }`}
                          >
                            {row.config}
                          </span>
                          {row.selected && (
                            <span className="rounded-full bg-gradient-to-r from-accent to-accent2 px-1.5 py-px font-mono text-[9px] font-bold uppercase tracking-wider text-[#080a16]">
                              selected
                            </span>
                          )}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-ink/75">
                        {row.llm}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-ink/75">
                        {row.embeddings}
                      </td>
                      <td className="px-3 py-2.5 font-mono tabular-nums text-ink/75">
                        {row.chunk}
                      </td>
                      <td className="px-3 py-2.5 font-mono tabular-nums text-ink/90">
                        {row.number}
                      </td>
                      <td className="px-3 py-2.5 font-mono tabular-nums text-ink/90">
                        {row.boundary}
                      </td>
                      <td
                        className={`px-3 py-2.5 font-mono tabular-nums ${
                          row.selected ? "font-semibold text-mint" : "text-ink/90"
                        }`}
                      >
                        {row.keyFacts}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2.5 px-1 text-[12px] leading-relaxed text-muted">
              gemini_native selected: highest number accuracy and retrieval
              richness; k=5 optimal by sweep (k=3→43%, k=5/8→70% key-facts).
            </p>
          </section>

          {/* C — Retrieval depth sweep */}
          <section aria-label="Retrieval depth sweep">
            <Eyebrow>Retrieval depth (k) sweep</Eyebrow>
            <div className="mt-3 space-y-2.5 rounded-xl bg-white/[0.025] px-4 py-3.5 ring-1 ring-inset ring-white/[0.06]">
              {K_SWEEP.map((row, i) => (
                <div key={row.k} className="flex items-center gap-3">
                  <span
                    className={`w-8 shrink-0 font-mono text-[12px] ${
                      row.selected ? "font-semibold text-white" : "text-muted"
                    }`}
                  >
                    k={row.k}
                  </span>
                  <div className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${row.keyFacts}%` }}
                      transition={{
                        delay: 0.2 + i * 0.09,
                        type: "spring",
                        stiffness: 110,
                        damping: 22,
                      }}
                      className={`h-full rounded-full ${
                        row.selected
                          ? "bg-gradient-to-r from-accent to-accent2 shadow-glow-cyan"
                          : "bg-white/20"
                      }`}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right font-mono text-[12px] tabular-nums text-ink/90">
                    {row.keyFacts}%
                  </span>
                </div>
              ))}
              <p className="pt-1 text-[12px] leading-relaxed text-muted">
                Key-facts hit-rate by retrieval depth. k=5 matches k=8 on
                accuracy at the lowest latency — deeper retrieval added
                context, not signal.
              </p>
            </div>
          </section>
        </div>
      </motion.div>
    </motion.div>
  );
}
