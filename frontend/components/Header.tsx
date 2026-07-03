"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

function Logo() {
  return (
    <div className="light-edge relative grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-accent to-accent2 shadow-glow">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path
          d="M6 4h9l3 3v13H6z"
          stroke="#080a16"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="M9 11h6M9 14.5h6M9 8h3"
          stroke="#080a16"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}

export function Header({ children }: { children?: ReactNode }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
      className="glass-panel light-edge z-30 flex shrink-0 flex-col gap-3 rounded-2xl px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5"
    >
      <div className="flex items-center gap-3.5">
        <Logo />
        <div className="min-w-0">
          <h1 className="font-display text-[18px] font-bold leading-none tracking-tight">
            <span className="text-aurora">10-K Intelligence</span>
          </h1>
          <p className="mt-1 truncate text-[12.5px] text-muted">
            Grounded answers across Alphabet, Amazon &amp; Microsoft filings
          </p>
        </div>
      </div>

      <div className="flex min-w-0 items-center gap-2 sm:justify-end">
        {children}
      </div>
    </motion.header>
  );
}
