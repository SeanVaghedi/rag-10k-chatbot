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
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{
        type: "spring",
        stiffness: 320,
        damping: 28,
        delay: index * 0.07,
      }}
      whileHover={{ y: -2 }}
      className="glass light-edge group relative overflow-hidden rounded-xl p-3.5"
    >
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
          <span className="rounded-full bg-white/6 px-2 py-0.5 font-mono text-[11px] text-muted ring-1 ring-inset ring-white/10">
            {sources.length}
          </span>
        )}
      </div>

      {hasSources ? (
        <motion.ul
          layout
          className="no-scrollbar flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto pr-0.5"
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
          <div className="light-edge glass mb-4 grid h-14 w-14 place-items-center rounded-2xl font-display text-xl text-muted">
            §
          </div>
          <p className="text-sm text-ink/80">No sources yet</p>
          <p className="mt-1 max-w-[220px] text-xs leading-relaxed text-muted">
            Ask a question and the filing excerpts used to ground the answer will
            appear here.
          </p>
        </div>
      )}
    </div>
  );
}
