"use client";

import { useRef } from "react";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  type Variants,
} from "framer-motion";
import type { Source } from "@/lib/types";

function titleCase(value: string | null): string {
  if (!value) return "Unknown";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/* --- Entrance choreography ------------------------------------------------
   Cards "materialize": they fly in from slightly behind the glass (smaller,
   blurred, tilted back 8°) and crystallize into place on a spring, cascading
   one after another via parent stagger. A brief accent glow pulses on the
   border as each card lands. The list is keyed per answer so the sequence
   replays on every new set of sources, not just first mount.

   Performance: only transform, opacity, and filter are animated; the glow is
   an opacity-only overlay (no box-shadow interpolation, and no inline
   box-shadow that would override the Tailwind hover/focus rings). */

const listVariants: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.07, delayChildren: 0.05 },
  },
  exit: { opacity: 0, transition: { duration: 0.16, ease: "easeIn" } },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 24, scale: 0.85, rotateX: 8, filter: "blur(8px)" },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    rotateX: 0,
    filter: "blur(0px)",
    // Spring on the transforms for an organic settle; tweens on opacity and
    // blur so neither overshoots into invalid/flickery territory.
    transition: {
      type: "spring",
      stiffness: 260,
      damping: 22,
      opacity: { type: "tween", duration: 0.35, ease: "easeOut" },
      filter: { type: "tween", duration: 0.4, ease: "easeOut" },
    },
  },
};

/* Reduced motion: a gentle fade + small rise. No 3D, no blur, no spring
   overshoot, no glow pulse. (The app-level MotionConfig reducedMotion="user"
   additionally strips transform animation, degrading this to a pure fade.) */
const cardVariantsReduced: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "tween", duration: 0.3, ease: "easeOut" },
  },
};

const glowVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: [0, 1, 0],
    transition: { delay: 0.1, duration: 0.5, times: [0, 0.45, 1], ease: "easeOut" },
  },
};

const glowVariantsReduced: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 0 },
};

function SourceCard({
  source,
  onOpen,
  reduced,
}: {
  source: Source;
  onOpen?: (s: Source) => void;
  reduced: boolean;
}) {
  const clickable = !!source.source_filename && !!onOpen;
  const open = () => clickable && onOpen?.(source);

  return (
    <motion.li
      variants={reduced ? cardVariantsReduced : cardVariants}
      whileHover={clickable ? { y: -2 } : undefined}
      onClick={open}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                open();
              }
            }
          : undefined
      }
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      aria-label={
        clickable
          ? `Open ${titleCase(source.company)} FY${source.year} filing at page ${source.page}`
          : undefined
      }
      className={`glass light-edge group relative overflow-hidden rounded-xl p-3.5 ${
        clickable
          ? "sheen cursor-pointer transition-colors hover:ring-1 hover:ring-inset hover:ring-accent2/40 focus:outline-none focus-visible:ring-1 focus-visible:ring-accent2/60"
          : ""
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-display text-sm font-semibold text-white">
          {titleCase(source.company)}
        </span>
        <div className="flex items-center gap-1.5">
          {clickable && (
            <span
              aria-hidden
              className="text-accent2 opacity-0 transition-opacity group-hover:opacity-100"
              title="Open PDF at this page"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                <path
                  d="M14 4h6v6M20 4l-8 8M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          )}
          {source.year != null && (
            <span className="rounded-md bg-accent/15 px-1.5 py-0.5 font-mono text-[11px] text-accent2 ring-1 ring-inset ring-accent/25">
              FY{source.year}
            </span>
          )}
        </div>
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

      {/* Landing glow — an accent pulse along the border as the card locks
          in. Opacity-only (GPU-cheap) and pointer-transparent, so the card
          stays fully clickable and its hover/focus rings keep working. */}
      <motion.span
        aria-hidden
        variants={reduced ? glowVariantsReduced : glowVariants}
        className="pointer-events-none absolute inset-0 rounded-xl"
        style={{
          boxShadow:
            "inset 0 0 0 1px rgba(139,125,255,0.55), inset 0 0 24px -8px rgba(139,125,255,0.45)",
        }}
      />
    </motion.li>
  );
}

export function SourcesPanel({
  sources,
  question,
  onOpenSource,
}: {
  sources: Source[];
  /** The question the selected answer responded to (shown as context). */
  question?: string | null;
  onOpenSource?: (s: Source) => void;
}) {
  const hasSources = sources.length > 0;
  const reduced = useReducedMotion() ?? false;

  // A new answer delivers a new sources array (token updates reuse the same
  // reference), so array identity marks "new answer". Bumping a generation
  // and keying the list with it makes AnimatePresence replay the cascade for
  // every answer. Guarded render-time ref writes are idempotent re-renders.
  const generationRef = useRef(0);
  const prevSourcesRef = useRef<Source[] | null>(null);
  if (prevSourcesRef.current !== sources) {
    prevSourcesRef.current = sources;
    generationRef.current += 1;
  }
  const generation = generationRef.current;

  return (
    <div className="flex h-full flex-col">
      <div className="px-1 pb-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-muted">
            Sources
          </h2>
          {hasSources && (
            <span className="rounded-full bg-white/6 px-2 py-0.5 font-mono text-[11px] text-muted ring-1 ring-inset ring-white/10">
              {sources.length}
            </span>
          )}
        </div>
        {hasSources && question && (
          <p
            className="mt-1.5 line-clamp-2 text-[12px] leading-snug text-muted"
            title={question}
          >
            “{question}”
          </p>
        )}
      </div>

      {hasSources ? (
        /* Perspective on the wrapper so each card's rotateX reads as true
           3D depth (coming from behind the glass), not a flat skew. */
        <div
          className="min-h-0 flex-1"
          style={{ perspective: "1000px" }}
        >
          <AnimatePresence mode="wait">
            <motion.ul
              key={generation}
              variants={listVariants}
              initial="hidden"
              animate="show"
              exit="exit"
              className="no-scrollbar flex h-full flex-col gap-2.5 overflow-y-auto pr-0.5"
            >
              {sources.map((source, i) => (
                <SourceCard
                  key={`${source.source_filename}-${source.page}-${i}`}
                  source={source}
                  onOpen={onOpenSource}
                  reduced={reduced}
                />
              ))}
            </motion.ul>
          </AnimatePresence>
        </div>
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
