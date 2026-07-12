"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { ProgressEvent } from "@/lib/types";

/**
 * The pipeline's real thinking steps, streamed from the backend.
 *
 * Live mode (answer not yet streaming): a vertical cascade of steps — each new
 * step springs in, completed steps dim behind a small check, the current step
 * pulses with a soft glass glow and shimmering label.
 *
 * Collapsed mode (answer streaming / done): a small "Thought process"
 * disclosure chip; expanding it replays the completed steps.
 *
 * Motion is gated app-wide by <MotionConfig reducedMotion="user"> plus the
 * global prefers-reduced-motion CSS rule, so springs/pulses collapse to simple
 * appearance for users who ask for less motion.
 */
export function ThinkingSteps({
  steps,
  live,
}: {
  steps: ProgressEvent[];
  live: boolean;
}) {
  const [open, setOpen] = useState(false);

  if (live) {
    return (
      <ol className="flex flex-col gap-2 py-0.5" aria-label="Working…">
        {steps.map((step, i) => (
          <StepRow
            key={`${step.stage}-${i}`}
            step={step}
            active={i === steps.length - 1}
            entrance
          />
        ))}
      </ol>
    );
  }

  return (
    <div className="mb-2.5">
      <motion.button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "tween", duration: 0.25, ease: "easeOut" }}
        className={[
          "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[11px] transition-colors",
          open
            ? "bg-accent/15 text-accent2 ring-1 ring-inset ring-accent/35"
            : "bg-white/5 text-muted ring-1 ring-inset ring-white/10 hover:bg-white/10 hover:text-ink",
        ].join(" ")}
      >
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"
            fill="currentColor"
          />
        </svg>
        Thought process
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden
          className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        >
          <path
            d="M6 9l6 6 6-6"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </motion.button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <ol className="mt-2.5 flex flex-col gap-2 border-l border-white/[0.08] pl-3">
              {steps.map((step, i) => (
                <StepRow key={`${step.stage}-${i}`} step={step} active={false} />
              ))}
            </ol>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StepRow({
  step,
  active,
  entrance,
}: {
  step: ProgressEvent;
  active: boolean;
  /** Animate this row in (fade + rise). Used for the live cascade. */
  entrance?: boolean;
}) {
  return (
    <motion.li
      initial={entrance ? { opacity: 0, y: 8 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 320, damping: 28 }}
      className="flex items-center gap-2.5"
    >
      <span className="relative grid h-4 w-4 shrink-0 place-items-center">
        {active ? (
          <>
            {/* soft pulsing glow behind the current step's glass bead */}
            <motion.span
              className="absolute inset-0 rounded-full bg-accent2/40 blur-[3px]"
              animate={{ scale: [1, 1.65, 1], opacity: [0.6, 0.18, 0.6] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            />
            <span className="h-2 w-2 rounded-full bg-gradient-to-br from-accent to-accent2 shadow-glow ring-1 ring-inset ring-white/30" />
          </>
        ) : (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M5 12.5l4.5 4.5L19 7.5"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-accent2/70"
            />
          </svg>
        )}
      </span>
      <span
        className={
          active
            ? "shimmer-text font-mono text-[12.5px] tracking-wide"
            : "font-mono text-[12.5px] tracking-wide text-muted/75"
        }
      >
        {step.label}
      </span>
    </motion.li>
  );
}
