"use client";

import { motion } from "framer-motion";
import type { ChatMessage } from "@/lib/types";
import { Markdown } from "./Markdown";
import { ThinkingIndicator } from "./ThinkingIndicator";

function AssistantMark() {
  return (
    <div className="relative mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-accent/80 to-accent2/70 shadow-glow">
      <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/25" />
      <span className="font-display text-[13px] font-bold text-[#0a0b18]">
        10K
      </span>
    </div>
  );
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const showThinking = message.streaming && !message.content && !message.error;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && <AssistantMark />}

      <div
        className={[
          "max-w-[85%] rounded-2xl px-4 py-3 text-[15px] leading-relaxed",
          isUser
            ? "bg-gradient-to-br from-accent/25 to-accent2/15 text-ink ring-1 ring-inset ring-accent/30 shadow-[0_8px_30px_-12px_rgba(139,125,255,0.5)]"
            : message.error
              ? "glass text-ink ring-1 ring-inset ring-rose-400/30"
              : "glass text-ink",
        ].join(" ")}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : showThinking ? (
          <ThinkingIndicator />
        ) : (
          <div className={message.streaming ? "caret" : undefined}>
            {message.error ? (
              <p className="flex items-start gap-2 text-rose-200">
                <span aria-hidden>⚠</span>
                <span className="whitespace-pre-wrap">{message.content}</span>
              </p>
            ) : (
              <Markdown>{message.content}</Markdown>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
