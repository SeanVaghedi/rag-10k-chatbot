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
  { label: "LLM", value: "Google Gemini 3.1 Pro (gemini-3.1-pro-preview)" },
  { label: "Embeddings", value: "gemini-embedding-001" },
  { label: "Vector store", value: "FAISS (local)" },
  {
    label: "Retrieval",
    value: "query decomposition → MMR reranking → top 10 (fetch 40)",
  },
  { label: "Chunk size / overlap", value: "1000 / 150 tokens" },
  {
    label: "Corpus",
    value: "Alphabet, Amazon, Microsoft 10-K filings (FY2025)",
  },
];

/** Performance on the CORE 24-question gold set (current pipeline: query
 * decomposition + MMR reranking + derived-metric prompt). The hard
 * multi-figure tier is scored separately (see HARD_TIER_NOTE) and is NOT
 * folded into these numbers. */
const PRODUCTION_METRICS: { label: string; value: string }[] = [
  { label: "Number accuracy", value: "100%" },
  { label: "Calculation accuracy", value: "100%" },
  { label: "Boundary accuracy", value: "100%" },
  { label: "Retrieval richness (key-facts, comparison questions)", value: "100%" },
  { label: "Avg latency", value: "~15s" },
];

/** The hard multi-figure tier, reported as its own boundary — deliberately
 * separate from the core-set metrics above. */
const HARD_TIER_NOTE =
  "On deliberately hard three-company, multi-statement questions, the " +
  "system fully answers those needing Microsoft and Alphabet data — " +
  "including segment-level margins — but does not consistently surface " +
  "Amazon's segment-level figures. On these it reports what it retrieves " +
  "and explicitly flags what it cannot, rather than fabricating. This is " +
  "a known, documented boundary, not a hidden failure.";

/** Retrieval optimization progression on the gold set: each stage's
 * key-facts hit-rate on comparison questions. `keyFacts` drives the bar
 * width; the final pipeline composes decomposition WITH reranking. */
const RETRIEVAL_AB: {
  name: string;
  keyFacts: number;
  valueLabel: string;
  meta: string;
  selected?: boolean;
}[] = [
  { name: "Baseline (top-k only)", keyFacts: 80, valueLabel: "80%", meta: "~8s" },
  {
    name: "MMR reranking",
    keyFacts: 91.7,
    valueLabel: "91.7%",
    meta: "~8s · deterministic",
  },
  {
    name: "+ Query decomposition",
    keyFacts: 100,
    valueLabel: "100%",
    meta: "~15s · one extra LLM call",
    selected: true,
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
    llm: "Gemini 3.1 Pro",
    embeddings: "Gemini",
    chunk: "1000",
    number: "100%",
    boundary: "100%",
    keyFacts: "80%",
    selected: true,
  },
  {
    config: "gemini_nomic_embed",
    llm: "Gemini 3.1 Pro",
    embeddings: "nomic (local)",
    chunk: "1000",
    number: "100%",
    boundary: "100%",
    keyFacts: "25%",
  },
  {
    config: "gemini_native_cs500",
    llm: "Gemini 3.1 Pro",
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
    number: "70%",
    boundary: "100%",
    keyFacts: "35%",
  },
  {
    config: "llama_gemini_embed",
    llm: "Llama 3.1 8B",
    embeddings: "Gemini",
    chunk: "1000",
    number: "70%",
    boundary: "100%",
    keyFacts: "37%",
  },
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

          {/* A2 — Core gold-set performance */}
          <section aria-label="Core gold-set performance">
            <Eyebrow>Core gold-set performance — 24 questions</Eyebrow>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5">
              {PRODUCTION_METRICS.map((m) => (
                <div
                  key={m.label}
                  className="rounded-xl bg-white/[0.025] px-3 py-2.5 ring-1 ring-inset ring-white/[0.06]"
                >
                  <div className="font-mono text-[16px] font-semibold tabular-nums text-ink">
                    {m.value}
                  </div>
                  <div className="mt-0.5 text-[10.5px] leading-tight text-muted">
                    {m.label}
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-2.5 px-1 text-[12px] leading-relaxed text-muted">
              Measured on the core 24-question gold set. Boundary accuracy =
              correctly refusing out-of-scope questions (projections,
              companies not in the corpus); calculation = derived metrics
              (growth rates, margins, dollar changes) computed from statement
              figures. The hard tier below is scored separately and is not
              included in these numbers.
            </p>
          </section>

          {/* A3 — Hard multi-figure tier (separate from the core numbers) */}
          <section aria-label="Hard multi-figure tier">
            <div className="flex items-center gap-2.5">
              <Eyebrow>Hard multi-figure tier</Eyebrow>
              <span className="inline-flex items-center rounded-full bg-amber-400/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-amber-300 ring-1 ring-inset ring-amber-400/25">
                known boundary
              </span>
            </div>
            <div className="mt-3 rounded-xl bg-white/[0.025] px-4 py-3.5 ring-1 ring-inset ring-white/[0.06]">
              <p className="text-[12.5px] leading-relaxed text-ink/85">
                {HARD_TIER_NOTE}
              </p>
            </div>
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
              gemini_native selected: 100% number and boundary accuracy with
              the richest retrieval of the five candidates.
            </p>
            <p className="mt-1.5 px-1 text-[11.5px] italic leading-relaxed text-muted/80">
              Comparison run at configuration-selection time; the selected
              configuration was subsequently optimized with query
              decomposition, MMR reranking, and derived-metric support.
            </p>
          </section>

          {/* B2 — Retrieval optimization (A/B) */}
          <section aria-label="Retrieval optimization">
            <Eyebrow>Retrieval optimization</Eyebrow>
            <div className="mt-3 space-y-3.5 rounded-xl bg-white/[0.025] px-4 py-3.5 ring-1 ring-inset ring-white/[0.06]">
              {RETRIEVAL_AB.map((row, i) => (
                <div key={row.name}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="flex min-w-0 items-center gap-2">
                      <span
                        className={`truncate text-[12.5px] ${
                          row.selected
                            ? "font-semibold text-white"
                            : "text-ink/80"
                        }`}
                      >
                        {row.name}
                      </span>
                      {row.selected && (
                        <span className="shrink-0 rounded-full bg-gradient-to-r from-accent to-accent2 px-1.5 py-px font-mono text-[9px] font-bold uppercase tracking-wider text-[#080a16]">
                          selected
                        </span>
                      )}
                    </span>
                    <span className="shrink-0 font-mono text-[11.5px] tabular-nums text-muted">
                      <span
                        className={
                          row.selected
                            ? "font-semibold text-mint"
                            : "text-ink/90"
                        }
                      >
                        {row.valueLabel}
                      </span>{" "}
                      · {row.meta}
                    </span>
                  </div>
                  <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/[0.06]">
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
                </div>
              ))}
              <p className="pt-0.5 text-[12px] leading-relaxed text-muted">
                Query decomposition selected (composed with MMR reranking): a
                multi-company question is split into targeted per-company
                sub-queries, so every named company&apos;s filing is searched
                — 100% key-facts on the comparison questions, at the cost of
                one extra LLM call per question.
              </p>
            </div>
          </section>
        </div>
      </motion.div>
    </motion.div>
  );
}
