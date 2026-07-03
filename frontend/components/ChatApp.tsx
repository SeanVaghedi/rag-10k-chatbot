"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import type { ChatMessage, ConfigInfo, Source } from "@/lib/types";
import { fetchConfigs, streamAsk } from "@/lib/api";
import { Background } from "./Background";
import { Header } from "./Header";
import { ConfigSwitcher } from "./ConfigSwitcher";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { SourcesPanel } from "./SourcesPanel";

const EXAMPLE_QUESTIONS = [
  "How much cash did Amazon hold at the end of fiscal 2024?",
  "Compare cloud revenue across Alphabet, Amazon, and Microsoft.",
  "What are Microsoft's most significant risk factors?",
  "How do R&D expenses compare between the three companies?",
];

const DEFAULT_CONFIG = "gemini_native";

export default function ChatApp() {
  const [configs, setConfigs] = useState<ConfigInfo[]>([]);
  const [configLoading, setConfigLoading] = useState(true);
  const [configError, setConfigError] = useState<string | null>(null);
  const [selected, setSelected] = useState(DEFAULT_CONFIG);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const loadConfigs = useCallback(async () => {
    setConfigLoading(true);
    setConfigError(null);
    try {
      const list = await fetchConfigs();
      setConfigs(list);
      setSelected((prev) => {
        if (list.some((c) => c.name === prev)) return prev;
        const firstBuilt = list.find((c) => c.index_built);
        return firstBuilt?.name ?? list[0]?.name ?? prev;
      });
    } catch (e) {
      setConfigError(
        e instanceof Error ? e.message : "Could not reach the backend.",
      );
    } finally {
      setConfigLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  // Abort any in-flight stream on unmount.
  useEffect(() => () => abortRef.current?.abort(), []);

  // Smooth auto-scroll as content streams in.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const selectedInfo = configs.find((c) => c.name === selected);
  const indexMissing = !!selectedInfo && !selectedInfo.index_built;

  const latestSources = useMemo<Source[]>(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "assistant" && m.sources && m.sources.length > 0) {
        return m.sources;
      }
    }
    return [];
  }, [messages]);

  const blocked = isStreaming || configError !== null || indexMissing;

  const inputHint = configError
    ? "Backend unavailable — is it running on :8000?"
    : indexMissing
      ? `Index not built for "${selectedInfo?.label}". Run: python scripts/build_index.py --config ${selected}`
      : null;

  const send = useCallback(
    async (raw?: string) => {
      const q = (raw ?? input).trim();
      if (!q || isStreaming || configError !== null || indexMissing) return;

      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "user", content: q },
        { id: assistantId, role: "assistant", content: "", streaming: true },
      ]);
      setInput("");
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      const patch = (updater: (m: ChatMessage) => ChatMessage) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? updater(m) : m)),
        );

      try {
        await streamAsk(
          q,
          selected,
          {
            onToken: (t) => patch((m) => ({ ...m, content: m.content + t })),
            onSources: (s) => patch((m) => ({ ...m, sources: s })),
            onError: (msg) =>
              patch((m) => ({
                ...m,
                content: m.content ? `${m.content}\n\n_${msg}_` : msg,
                error: true,
                streaming: false,
              })),
          },
          controller.signal,
        );
      } catch (e) {
        if (controller.signal.aborted) return;
        const msg = e instanceof Error ? e.message : "Something went wrong.";
        patch((m) => ({
          ...m,
          content: m.content || msg,
          error: true,
          streaming: false,
        }));
      } finally {
        patch((m) => ({ ...m, streaming: false }));
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [input, isStreaming, selected, configError, indexMissing],
  );

  const isEmpty = messages.length === 0;

  return (
    <MotionConfig reducedMotion="user">
      <div className="relative mx-auto flex h-[100dvh] w-full max-w-[1500px] flex-col gap-3 p-3 sm:gap-4 sm:p-4">
        <Background />

        <Header>
          <div className="min-w-0 flex-1 sm:flex-none">
            <ConfigSwitcher
              configs={configs}
              selected={selected}
              onSelect={setSelected}
              disabled={isStreaming}
              loading={configLoading}
            />
          </div>
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="glass light-edge relative grid h-10 w-10 shrink-0 place-items-center rounded-xl text-muted transition-colors hover:text-ink lg:hidden"
            aria-label="Open sources"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M4 6h16M4 12h16M4 18h10"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
            {latestSources.length > 0 && (
              <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-accent px-1 font-mono text-[10px] text-[#080a16]">
                {latestSources.length}
              </span>
            )}
          </button>
        </Header>

        <main className="flex min-h-0 flex-1 gap-3 sm:gap-4">
          {/* Chat — the focal bento cell */}
          <section className="glass-panel light-edge flex min-w-0 flex-1 flex-col overflow-hidden rounded-3xl">
            {configError && (
              <div className="m-3 flex items-center justify-between gap-3 rounded-xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 sm:mx-5 sm:mt-5">
                <p className="text-sm text-rose-100">
                  Can&apos;t reach the backend. Start the API on port 8000, then
                  retry.
                </p>
                <button
                  type="button"
                  onClick={loadConfigs}
                  className="shrink-0 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-white/20"
                >
                  Retry
                </button>
              </div>
            )}

            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto px-4 py-6 sm:px-6"
            >
              {isEmpty ? (
                <EmptyState onPick={(q) => send(q)} disabled={blocked} />
              ) : (
                <div className="mx-auto flex max-w-3xl flex-col gap-5">
                  {messages.map((m) => (
                    <MessageBubble key={m.id} message={m} />
                  ))}
                </div>
              )}
            </div>

            <div className="shrink-0 border-t border-white/[0.06] px-4 pb-4 pt-3 sm:px-6">
              <ChatInput
                value={input}
                onChange={setInput}
                onSend={() => send()}
                disabled={blocked}
                streaming={isStreaming}
                hint={inputHint}
                placeholder={
                  indexMissing
                    ? "Select a config whose index is built…"
                    : "Ask about the filings…"
                }
              />
            </div>
          </section>

          {/* Sources — secondary bento cell (desktop) */}
          <aside className="glass-panel light-edge hidden w-[358px] shrink-0 flex-col rounded-3xl p-5 lg:flex">
            <SourcesPanel sources={latestSources} />
          </aside>
        </main>

        {/* Sources — drawer (mobile) */}
        <AnimatePresence>
          {drawerOpen && (
            <>
              <motion.div
                className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setDrawerOpen(false)}
              />
              <motion.aside
                className="glass-panel light-edge fixed right-0 top-0 z-50 flex h-[100dvh] w-[86%] max-w-[360px] flex-col p-5 lg:hidden"
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", damping: 32, stiffness: 300 }}
              >
                <div className="mb-2 flex items-center justify-end">
                  <button
                    type="button"
                    onClick={() => setDrawerOpen(false)}
                    className="grid h-8 w-8 place-items-center rounded-lg text-muted transition-colors hover:bg-white/10 hover:text-ink"
                    aria-label="Close sources"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                      <path
                        d="M6 6l12 12M18 6L6 18"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                  </button>
                </div>
                <div className="min-h-0 flex-1">
                  <SourcesPanel sources={latestSources} />
                </div>
              </motion.aside>
            </>
          )}
        </AnimatePresence>
      </div>
    </MotionConfig>
  );
}

function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (q: string) => void;
  disabled?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 220, damping: 28 }}
      className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center"
    >
      <motion.div
        className="light-edge mb-6 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-accent to-accent2 shadow-glow"
        animate={{ y: [0, -7, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      >
        <span className="font-display text-lg font-bold text-[#080a16]">
          10K
        </span>
      </motion.div>

      <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
        <span className="text-aurora">Interrogate the filings</span>
      </h2>
      <p className="mt-3 max-w-md text-[15px] leading-relaxed text-muted">
        Ask grounded questions across the latest 10-K filings of Alphabet,
        Amazon, and Microsoft. Every answer cites the filing, fiscal year, and
        page it draws from.
      </p>

      <div className="mt-8 grid w-full gap-2.5 sm:grid-cols-2">
        {EXAMPLE_QUESTIONS.map((q, i) => (
          <motion.button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onPick(q)}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12 + i * 0.07, type: "spring", stiffness: 260, damping: 26 }}
            whileHover={disabled ? undefined : { y: -3 }}
            className="glass light-edge group rounded-xl px-4 py-3 text-left text-sm text-ink/90 transition-colors hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="mr-2 font-mono text-accent2/80 transition-transform group-hover:translate-x-0.5">
              →
            </span>
            {q}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
