import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#070810",
        ink: "#e9edf7",
        muted: "#8b93a9",
        faint: "#5a6178",
        line: "rgba(255,255,255,0.08)",
        surface: "rgba(255,255,255,0.035)",
        accent: "#8b7dff",
        accent2: "#3fe0ff",
        good: "#4ade80",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 50px -12px rgba(139,125,255,0.55)",
        "glow-cyan": "0 0 40px -10px rgba(63,224,255,0.5)",
        panel: "0 24px 60px -24px rgba(0,0,0,0.7)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-14px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.22,1,0.36,1) both",
        float: "float 8s ease-in-out infinite",
      },
    },
  },
  plugins: [typography],
};

export default config;
