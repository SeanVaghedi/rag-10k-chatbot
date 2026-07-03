"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

function Logo() {
  return (
    <div className="relative grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-accent to-accent2 shadow-glow">
      <div className="absolute inset-0 rounded-2xl ring-1 ring-inset ring-white/25" />
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
        <path
          d="M6 4h9l3 3v13H6z"
          stroke="#0a0b18"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="M9 11h6M9 14.5h6M9 8h3"
          stroke="#0a0b18"
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
      initial={{ opacity: 0, y: -14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="sticky top-0 z-30 border-b border-line bg-bg/40 backdrop-blur-xl"
    >
      <div className="mx-auto flex max-w-[1400px] flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-3.5">
          <Logo />
          <div className="min-w-0">
            <h1 className="font-display text-[17px] font-bold leading-tight tracking-tight">
              <span className="text-gradient">10-K Intelligence</span>
            </h1>
            <p className="truncate text-[12.5px] text-muted">
              Grounded answers across Alphabet, Amazon &amp; Microsoft filings
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">{children}</div>
      </div>
    </motion.header>
  );
}
