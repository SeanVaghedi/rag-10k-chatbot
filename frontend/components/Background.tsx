"use client";

import { motion } from "framer-motion";

/**
 * Calm ambient backdrop: three slow, softly-drifting aurora fields — one per
 * filing in the corpus (iris, cyan, mint) — beneath a faint structural grid
 * and a whisper of grain. Deliberately low-contrast so it reads as depth,
 * never as decoration competing with the glass surfaces. Motion loops are
 * transform-only and are frozen under reduced-motion via the app-level
 * <MotionConfig reducedMotion="user">.
 */
export function Background() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <div className="absolute inset-0 bg-[radial-gradient(130%_120%_at_50%_-15%,#12142c_0%,#0a0b18_46%,#06070e_100%)]" />

      <motion.div
        className="absolute -top-[20%] left-1/2 h-[62vh] w-[62vh] -translate-x-1/2 rounded-full bg-[#5b4bff]/20 blur-[150px]"
        animate={{ x: [-50, 50, -50], y: [-16, 26, -16], scale: [1, 1.1, 1] }}
        transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-[-18%] right-[-8%] h-[54vh] w-[54vh] rounded-full bg-[#12c8ff]/14 blur-[150px]"
        animate={{ x: [0, -60, 0], y: [0, 34, 0], scale: [1.05, 1, 1.05] }}
        transition={{ duration: 34, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-[-14%] left-[-10%] h-[46vh] w-[46vh] rounded-full bg-[#86ffd0]/[0.07] blur-[150px]"
        animate={{ x: [0, 44, 0], y: [0, -26, 0], scale: [1, 1.08, 1] }}
        transition={{ duration: 41, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="bg-grid absolute inset-0 opacity-[0.04]" />
      <div className="bg-noise absolute inset-0 opacity-[0.03] mix-blend-soft-light" />
      <div className="absolute inset-0 bg-[radial-gradient(120%_100%_at_50%_50%,transparent_58%,rgba(0,0,0,0.6)_100%)]" />
    </div>
  );
}
