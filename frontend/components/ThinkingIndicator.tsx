"use client";

import { motion } from "framer-motion";

/**
 * A soft pulsing glass orb — a small frosted sphere with an inner specular
 * highlight that breathes — paired with a shimmering status line. Reads as the
 * model "considering," not a generic spinner.
 */
export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative h-6 w-6">
        {/* diffuse aura */}
        <motion.span
          className="absolute inset-0 rounded-full bg-accent2/40 blur-md"
          animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0.15, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* glass sphere */}
        <motion.span
          className="absolute inset-0 rounded-full bg-gradient-to-br from-white/25 to-white/5 ring-1 ring-inset ring-white/25 backdrop-blur-sm"
          animate={{ scale: [1, 0.92, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* specular highlight */}
        <motion.span
          className="absolute left-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-white/90 blur-[1px]"
          animate={{ opacity: [0.9, 0.4, 0.9] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <span className="shimmer-text font-mono text-[13px] tracking-wide">
        Reading the filings
      </span>
    </div>
  );
}
