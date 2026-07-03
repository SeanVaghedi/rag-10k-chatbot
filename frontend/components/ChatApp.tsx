"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
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
    <div className="relative flex h-[100dvh] flex-col overflow-hidden">
      <Background />

      <Header>
        <ConfigSwitcher
          configs={configs}
          selected={selected}
          onSelect={setSelected}
          disabled={isStreaming}
          loading={configLoading}
        />
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className="relative grid h-[42px] w-[42px] shrink-0 place-items-center rounded-xl glass text-muted transition-colors hover:text-ink lg:hidden"
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
            <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-accent px-1 font-mono text-[10px] text-[#0a0b18]">
              {latestSources.length}
            </span>
          )}
        </button>
      </Header>

      <main className="mx-auto flex w-full max-w-[1400px] min-h-0 flex-1 overflow-hidden">
        {/* Chat column */}
        <section className="flex min-w-0 flex-1 flex-col">
          {configError && (
            <div className="mx-4 mt-4 flex items-center justify-between gap-3 rounded-xl border border-rose-400/25 bg-rose-500/10 px-4 py-3 sm:mx-6">
              <p className="text-sm text-rose-100">
                Can&apos;t reach the backend. Make sure FastAPI is running on
                port 8000.
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
              <EmptyState
                onPick={(q) => send(q)}
                disabled={blocked}
              />
            ) : (
              <div className="mx-auto flex max-w-3xl flex-col gap-5">
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} />
                ))}
              </div>
            )}
          </div>

          <div className="shrink-0 px-4 pb-5 pt-2 sm:px-6">
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

        {/* Desktop sources */}
        <aside className="hidden w-[360px] shrink-0 border-l border-line p-5 lg:block">
          <SourcesPanel sources={latestSources} />
        </aside>
      </main>

      {/* Mobile sources drawer */}
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
              className="glass-strong fixed right-0 top-0 z-50 flex h-[100dvh] w-[86%] max-w-[360px] flex-col p-5 lg:hidden"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 280 }}
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
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center"
    >
      <motion.div
        className="mb-6 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-accent to-accent2 shadow-glow"
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      >
        <span className="font-display text-xl font-bold text-[#0a0b18]">
          10K
        </span>
      </motion.div>

      <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
        <span className="text-gradient">Interrogate the filings</span>
      </h2>
      <p className="mt-3 max-w-md text-[15px] leading-relaxed text-muted">
        Ask grounded questions across the latest 10-K filings of Alphabet,
        Amazon, and Microsoft. Every answer cites the exact filing, fiscal year,
        and page it draws from.
      </p>

      <div className="mt-8 grid w-full gap-2.5 sm:grid-cols-2">
        {EXAMPLE_QUESTIONS.map((q, i) => (
          <motion.button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onPick(q)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 + i * 0.07, duration: 0.4 }}
            className="group glass rounded-xl px-4 py-3 text-left text-sm text-ink/90 transition-all hover:ring-1 hover:ring-inset hover:ring-accent/40 disabled:cursor-not-allowed disabled:opacity-50"
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
