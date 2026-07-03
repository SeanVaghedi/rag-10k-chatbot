"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled?: boolean;
  streaming?: boolean;
  placeholder?: string;
  hint?: string | null;
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
  streaming,
  placeholder,
  hint,
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSend();
    }
  }

  const canSend = !disabled && value.trim().length > 0;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="glass light-edge relative flex items-end gap-2 rounded-2xl p-2 transition-shadow focus-within:shadow-glow-cyan">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? "Ask about the filings…"}
          className="max-h-[200px] flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] leading-relaxed text-ink placeholder:text-faint focus:outline-none disabled:opacity-60"
        />
        <motion.button
          type="button"
          onClick={onSend}
          disabled={!canSend}
          aria-label="Send message"
          whileHover={canSend ? { scale: 1.05 } : undefined}
          whileTap={canSend ? { scale: 0.94 } : undefined}
          className="light-edge group relative grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-accent to-accent2 text-[#080a16] transition-shadow hover:shadow-glow disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
        >
          {streaming ? (
            <motion.span
              className="h-3 w-3 rounded-[3px] bg-[#080a16]"
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M5 12h14M13 6l6 6-6 6"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </motion.button>
      </div>
      <div className="px-2 pt-2">
        <p className="text-[11.5px] text-muted">
          {hint ?? (
            <>
              <kbd className="font-mono text-ink/70">Enter</kbd> to send ·{" "}
              <kbd className="font-mono text-ink/70">Shift + Enter</kbd> for a
              new line
            </>
          )}
        </p>
      </div>
    </div>
  );
}
