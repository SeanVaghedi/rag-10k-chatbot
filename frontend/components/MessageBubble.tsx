"use client";

import { motion } from "framer-motion";
import type { ChatMessage } from "@/lib/types";
import { Markdown } from "./Markdown";
import { ThinkingIndicator } from "./ThinkingIndicator";

function AssistantMark() {
  return (
    <div className="light-edge relative mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-accent/85 to-accent2/70 shadow-glow">
      <span className="font-display text-[12px] font-bold text-[#080a16]">
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
      initial={{ opacity: 0, y: 14, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 30 }}
      className={`flex w-full gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && <AssistantMark />}

      <div
        className={[
          "light-edge max-w-[85%] rounded-2xl px-4 py-3 text-[15px] leading-relaxed",
          isUser
            ? "bg-gradient-to-br from-accent/22 to-accent2/12 text-ink shadow-[0_10px_36px_-16px_rgba(139,125,255,0.55)]"
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
