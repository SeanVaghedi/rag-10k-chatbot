import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#06070e",
        ink: "#eef1fa",
        muted: "#9aa2b8",
        faint: "#646c82",
        line: "rgba(255,255,255,0.09)",
        // Restrained aurora accent — used only for state + emphasis.
        accent: "#8b7dff", // iris / violet
        accent2: "#4fe3ff", // cyan
        mint: "#86ffd0", // aurora highlight (used sparingly)
        good: "#57e389",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px -10px rgba(139,125,255,0.5)",
        "glow-cyan": "0 0 36px -12px rgba(79,227,255,0.5)",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.22,1,0.36,1)",
      },
    },
  },
  plugins: [typography],
};

export default config;
