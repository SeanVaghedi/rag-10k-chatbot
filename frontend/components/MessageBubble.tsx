"use client";

import { motion } from "framer-motion";
import type { ChatMessage } from "@/lib/types";
import { Markdown } from "./Markdown";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { ThinkingSteps } from "./ThinkingSteps";

function AssistantMark() {
  return (
    <div className="light-edge relative mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-accent/85 to-accent2/70 shadow-glow">
      <span className="font-display text-[12px] font-bold text-[#080a16]">
        10K
      </span>
    </div>
  );
}

export function MessageBubble({
  message,
  selected,
  onSelectSources,
  onRetry,
}: {
  message: ChatMessage;
  /** True when the sources panel is showing this answer's sources. */
  selected?: boolean;
  /** Selects this answer's sources into the panel (via the badge). */
  onSelectSources?: () => void;
  /** Re-asks this answer's question after an error. Only passed for error
   * bubbles while nothing else is streaming. */
  onRetry?: () => void;
}) {
  const isUser = message.role === "user";
  const showThinking = message.streaming && !message.content && !message.error;
  const thinkingSteps = message.thinking ?? [];
  const hasThinking = thinkingSteps.length > 0;
  const sourceCount = message.sources?.length ?? 0;
  const showBadge = !isUser && !message.error && sourceCount > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 30 }}
      className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && <AssistantMark />}

      <div
        className={[
          "light-edge max-w-[85%] rounded-2xl px-4 py-3 text-[15px] leading-relaxed transition-shadow duration-500",
          isUser
            ? "bg-gradient-to-br from-accent/22 to-accent2/12 text-ink shadow-[0_10px_36px_-16px_rgba(139,125,255,0.55)]"
            : message.error
              ? "glass text-ink ring-1 ring-inset ring-rose-400/30"
              : selected
                ? "glass text-ink ring-1 ring-inset ring-accent/40 shadow-[0_0_38px_-14px_rgba(139,125,255,0.65)]"
                : "glass text-ink",
        ].join(" ")}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : showThinking ? (
          // Live pipeline steps when the backend streams them; the classic
          // orb indicator when it doesn't (older backend — graceful fallback).
          hasThinking ? (
            <ThinkingSteps steps={thinkingSteps} live />
          ) : (
            <ThinkingIndicator />
          )
        ) : (
          <>
            {hasThinking && !message.error && (
              <ThinkingSteps steps={thinkingSteps} live={false} />
            )}
            <div className={message.streaming ? "caret" : undefined}>
              {message.error ? (
                <div className="flex flex-col gap-2.5">
                  <p className="flex items-start gap-2 text-rose-200">
                    <span aria-hidden>⚠</span>
                    <span className="whitespace-pre-wrap">
                      {message.content}
                    </span>
                  </p>
                  {onRetry && (
                    <button
                      type="button"
                      onClick={onRetry}
                      className="inline-flex items-center gap-1.5 self-start rounded-full bg-white/5 px-2.5 py-1 font-mono text-[11px] text-muted ring-1 ring-inset ring-white/10 transition-colors hover:bg-white/10 hover:text-ink"
                    >
                      <svg
                        width="11"
                        height="11"
                        viewBox="0 0 24 24"
                        fill="none"
                        aria-hidden
                      >
                        <path
                          d="M20 12a8 8 0 1 1-2.34-5.66M20 4v4h-4"
                          stroke="currentColor"
                          strokeWidth="2.2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      Retry
                    </button>
                  )}
                </div>
              ) : (
                <Markdown>{message.content}</Markdown>
              )}
            </div>
          </>
        )}

        {/* Sources badge — selects this answer's sources into the panel. */}
        {showBadge && (
          <motion.button
            type="button"
            onClick={onSelectSources}
            aria-pressed={selected}
            aria-label={`Show the ${sourceCount} source${
              sourceCount === 1 ? "" : "s"
            } for this answer`}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "tween", duration: 0.25, ease: "easeOut" }}
            className={[
              "mt-3 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[11px] transition-colors",
              selected
                ? "bg-accent/15 text-accent2 ring-1 ring-inset ring-accent/35"
                : "bg-white/5 text-muted ring-1 ring-inset ring-white/10 hover:bg-white/10 hover:text-ink",
            ].join(" ")}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M4 6h16M4 12h16M4 18h10"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
            {sourceCount} source{sourceCount === 1 ? "" : "s"}
          </motion.button>
        )}
      </div>
    </motion.div>
  );
}
