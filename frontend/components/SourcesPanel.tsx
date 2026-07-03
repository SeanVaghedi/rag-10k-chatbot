"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { Source } from "@/lib/types";

function titleCase(value: string | null): string {
  if (!value) return "Unknown";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 14, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{
        duration: 0.4,
        delay: index * 0.06,
        ease: [0.22, 1, 0.36, 1],
      }}
      className="group relative overflow-hidden rounded-xl glass p-3.5 transition-colors hover:ring-1 hover:ring-inset hover:ring-accent/30"
    >
      <div
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/60 to-transparent opacity-0 transition-opacity group-hover:opacity-100"
        aria-hidden
      />
      <div className="flex items-center justify-between gap-2">
        <span className="font-display text-sm font-semibold text-white">
          {titleCase(source.company)}
        </span>
        {source.year != null && (
          <span className="rounded-md bg-accent/15 px-1.5 py-0.5 font-mono text-[11px] text-accent2 ring-1 ring-inset ring-accent/25">
            FY{source.year}
          </span>
        )}
      </div>
      <div className="mt-2 flex items-center gap-2 font-mono text-[11px] text-muted">
        {source.page != null && (
          <span className="rounded bg-white/5 px-1.5 py-0.5">
            p.{source.page}
          </span>
        )}
        <span className="truncate" title={source.source_filename ?? undefined}>
          {source.source_filename ?? "unknown source"}
        </span>
      </div>
    </motion.li>
  );
}

export function SourcesPanel({ sources }: { sources: Source[] }) {
  const hasSources = sources.length > 0;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-1 pb-3">
        <h2 className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-muted">
          Sources
        </h2>
        {hasSources && (
          <span className="rounded-full bg-white/5 px-2 py-0.5 font-mono text-[11px] text-muted">
            {sources.length}
          </span>
        )}
      </div>

      {hasSources ? (
        <motion.ul
          layout
          className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto pr-1"
        >
          <AnimatePresence mode="popLayout">
            {sources.map((source, i) => (
              <SourceCard
                key={`${source.source_filename}-${source.page}-${i}`}
                source={source}
                index={i}
              />
            ))}
          </AnimatePresence>
        </motion.ul>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center px-4 text-center">
          <div className="relative mb-4 h-14 w-14">
            <div className="absolute inset-0 rounded-2xl glass" />
            <div className="absolute inset-0 grid place-items-center font-display text-xl text-muted">
              §
            </div>
          </div>
          <p className="text-sm text-muted">No sources yet</p>
          <p className="mt-1 max-w-[220px] text-xs leading-relaxed text-faint">
            Ask a question and the filing excerpts used to ground the answer will
            appear here.
          </p>
        </div>
      )}
    </div>
  );
}
