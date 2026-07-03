"use client";

import { motion } from "framer-motion";

/** Glowing, pulsing indicator shown while awaiting the first streamed token. */
export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative h-2.5 w-2.5">
        <motion.span
          className="absolute inset-0 rounded-full bg-accent"
          animate={{ scale: [1, 1.6, 1], opacity: [0.9, 0.4, 0.9] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.span
          className="absolute inset-0 rounded-full bg-accent blur-[6px]"
          animate={{ scale: [1, 2.2, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <span className="shimmer-text font-mono text-[13px] tracking-wide">
        Reading the filings
      </span>
    </div>
  );
}
