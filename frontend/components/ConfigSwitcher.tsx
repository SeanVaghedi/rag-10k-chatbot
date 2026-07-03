"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { ConfigInfo } from "@/lib/types";

function StatusDot({ built }: { built: boolean }) {
  return (
    <span className="relative inline-flex h-2 w-2 shrink-0">
      <span
        className={`absolute inset-0 rounded-full ${
          built ? "bg-good" : "bg-faint"
        }`}
      />
      {built && (
        <span className="absolute inset-0 animate-ping rounded-full bg-good/70" />
      )}
    </span>
  );
}

interface Props {
  configs: ConfigInfo[];
  selected: string;
  onSelect: (name: string) => void;
  disabled?: boolean;
  loading?: boolean;
}

export function ConfigSwitcher({
  configs,
  selected,
  onSelect,
  disabled,
  loading,
}: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, []);

  const current = configs.find((c) => c.name === selected);
  const label = loading
    ? "Loading configs…"
    : (current?.label ?? selected);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        disabled={disabled || loading}
        onClick={() => setOpen((o) => !o)}
        className="group flex w-full items-center gap-2.5 rounded-xl glass px-3.5 py-2.5 text-left transition-colors hover:ring-1 hover:ring-inset hover:ring-accent/30 disabled:cursor-not-allowed disabled:opacity-60 sm:w-[260px]"
      >
        {current ? (
          <StatusDot built={current.index_built} />
        ) : (
          <span className="h-2 w-2 rounded-full bg-faint" />
        )}
        <span className="flex-1 truncate text-sm font-medium text-ink">
          {label}
        </span>
        <motion.svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-muted"
        >
          <path
            d="M6 9l6 6 6-6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </motion.svg>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            className="glass-strong absolute right-0 z-50 mt-2 w-[280px] origin-top-right overflow-hidden rounded-xl p-1.5 shadow-panel"
          >
            <p className="px-2.5 pb-1.5 pt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
              Provider configuration
            </p>
            {configs.map((c) => {
              const isSelected = c.name === selected;
              const notBuilt = !c.index_built;
              return (
                <button
                  key={c.name}
                  type="button"
                  disabled={notBuilt}
                  title={notBuilt ? "Index not built yet" : undefined}
                  onClick={() => {
                    if (notBuilt) return;
                    onSelect(c.name);
                    setOpen(false);
                  }}
                  className={[
                    "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors",
                    notBuilt
                      ? "cursor-not-allowed opacity-45"
                      : "hover:bg-white/5",
                    isSelected ? "bg-white/[0.07]" : "",
                  ].join(" ")}
                >
                  <StatusDot built={c.index_built} />
                  <span className="flex-1 truncate text-sm text-ink">
                    {c.label}
                  </span>
                  {notBuilt ? (
                    <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-faint">
                      not built
                    </span>
                  ) : isSelected ? (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      className="text-accent2"
                    >
                      <path
                        d="M5 13l4 4L19 7"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : null}
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
