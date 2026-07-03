"use client";

import { motion } from "framer-motion";

/**
 * Ambient animated backdrop: slow-drifting color fields behind a fine grid and
 * a whisper of film grain. Purely decorative, non-interactive, and kept low
 * enough in contrast that it never competes with the content.
 */
export function Background() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      {/* deep base gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(120%_120%_at_50%_-10%,#101430_0%,#0a0b18_45%,#070810_100%)]" />

      {/* drifting aurora fields */}
      <motion.div
        className="absolute -top-1/4 left-1/2 h-[60vh] w-[60vh] -translate-x-1/2 rounded-full bg-[#5b4bff]/25 blur-[130px]"
        animate={{ x: [-60, 60, -60], y: [-20, 30, -20], scale: [1, 1.12, 1] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-1/3 -left-24 h-[46vh] w-[46vh] rounded-full bg-[#12d6ff]/16 blur-[120px]"
        animate={{ x: [0, 80, 0], y: [0, -40, 0], scale: [1, 1.18, 1] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-[-20%] right-[-10%] h-[52vh] w-[52vh] rounded-full bg-[#a855f7]/16 blur-[130px]"
        animate={{ x: [0, -70, 0], y: [0, 40, 0], scale: [1.05, 1, 1.05] }}
        transition={{ duration: 30, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* structural grid */}
      <div className="bg-grid absolute inset-0 opacity-[0.05]" />

      {/* grain */}
      <div className="bg-noise absolute inset-0 opacity-[0.035] mix-blend-soft-light" />

      {/* vignette to seat the content */}
      <div className="absolute inset-0 bg-[radial-gradient(120%_100%_at_50%_50%,transparent_55%,rgba(0,0,0,0.55)_100%)]" />
    </div>
  );
}
