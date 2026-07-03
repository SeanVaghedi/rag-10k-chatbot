"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { motion } from "framer-motion";
import type { Source } from "@/lib/types";
import { API_URL } from "@/lib/api";
import { computeMatchedSpans, type HighlightOutcome } from "@/lib/pdfMatch";
// Text layer CSS is required for correct span positioning (highlighting needs it).
import "react-pdf/dist/esm/Page/TextLayer.css";

// The pdf.js worker is copied into public/ by scripts/copy-pdf-worker.mjs
// (wired into predev/prebuild) and served as a static asset. react-pdf 7 /
// pdfjs-dist 3 use the classic .js worker, which Next.js 14 serves as a
// standard (non-module) worker — no ESM bundling issues.
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.js";

function titleCase(value: string | null): string {
  if (!value) return "Unknown";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function Spinner({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted">
      <span className="h-8 w-8 animate-spin rounded-full border-2 border-white/15 border-t-accent2" />
      <span className="font-mono text-xs">{label}</span>
    </div>
  );
}

function NavButton({
  onClick,
  disabled,
  dir,
}: {
  onClick: () => void;
  disabled: boolean;
  dir: "prev" | "next";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={dir === "prev" ? "Previous page" : "Next page"}
      className="glass light-edge grid h-8 w-8 place-items-center rounded-lg text-ink transition-colors hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
        <path
          d={dir === "prev" ? "M15 6l-6 6 6 6" : "M9 6l6 6-6 6"}
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}

function HighlightNote({ outcome }: { outcome: HighlightOutcome }) {
  const map = {
    full: { dot: "bg-accent2", text: "Highlighted cited passage" },
    partial: { dot: "bg-amber-400", text: "Cited page · partial highlight" },
    none: { dot: "bg-faint", text: "Showing cited page" },
  } as const;
  const { dot, text } = map[outcome];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-white/5 px-1.5 py-0.5 font-mono text-[11px] text-muted ring-1 ring-inset ring-white/10">
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {text}
    </span>
  );
}

interface Props {
  source: Source;
  onClose: () => void;
}

export default function PdfViewerModal({ source, onClose }: Props) {
  const filename = source.source_filename ?? "";
  const url = `${API_URL}/pdfs/${encodeURIComponent(filename)}`;
  const chunkText = source.chunk_text ?? "";
  const hasChunk = chunkText.trim().length > 0;

  // source.page is already 1-based (loader uses `enumerate(pages, start=1)`),
  // and react-pdf's Page `pageNumber` is also 1-based — so use it directly.
  const targetPage = Math.max(1, source.page ?? 1);

  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(targetPage);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [pageWidth, setPageWidth] = useState(720);
  const [highlightStatus, setHighlightStatus] = useState<
    "pending" | HighlightOutcome
  >("pending");

  const bodyRef = useRef<HTMLDivElement>(null);
  const pageWrapRef = useRef<HTMLDivElement>(null);
  const didScrollRef = useRef(false);

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Fit the rendered page to the modal body width.
  useLayoutEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    const measure = () => setPageWidth(Math.min(el.clientWidth - 32, 900));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // On page change: reset scroll + highlight state (highlights recompute when
  // the new page's text layer renders).
  useEffect(() => {
    didScrollRef.current = false;
    setHighlightStatus("pending");
    bodyRef.current?.scrollTo({ top: 0 });
  }, [pageNumber]);

  const onLoadSuccess = useCallback(
    ({ numPages: total }: { numPages: number }) => {
      setNumPages(total);
      setPageNumber((p) => Math.min(Math.max(1, p), total));
    },
    [],
  );

  const go = (delta: number) =>
    setPageNumber((p) => {
      const max = numPages ?? p;
      return Math.min(Math.max(1, p + delta), max);
    });

  const retry = () => {
    setError(null);
    setNumPages(null);
    setPageNumber(targetPage);
    setHighlightStatus("pending");
    didScrollRef.current = false;
    setReloadKey((k) => k + 1);
  };

  // Apply highlights over the rendered text layer. Fully defensive: any failure
  // leaves the page displayed exactly as before (page-jump is never blocked).
  const applyHighlights = useCallback(() => {
    const wrap = pageWrapRef.current;
    if (!wrap) return;
    const layer =
      wrap.querySelector(".react-pdf__Page__textContent") ??
      wrap.querySelector(".textLayer");
    if (!layer) return;

    // Clear any prior marks (text layer is rebuilt on resize / page change).
    layer.querySelectorAll("span.pdf-hl").forEach((el) => {
      el.classList.remove("pdf-hl");
      (el as HTMLElement).style.animationDelay = "";
    });

    if (!hasChunk || pageNumber !== targetPage) {
      setHighlightStatus("none");
      return;
    }

    const spanEls = Array.from(layer.querySelectorAll("span")).filter(
      (el) =>
        (el.textContent || "").trim().length > 0 &&
        !el.classList.contains("markedContent"),
    ) as HTMLElement[];

    const { matched, outcome } = computeMatchedSpans(spanEls, chunkText);
    matched.forEach((el, i) => {
      el.classList.add("pdf-hl");
      el.style.animationDelay = `${Math.min(i * 18, 320)}ms`;
    });

    if (matched.length && !didScrollRef.current) {
      didScrollRef.current = true;
      const reduce =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      matched[0].scrollIntoView({
        block: "center",
        behavior: reduce ? "auto" : "smooth",
      });
    }
    setHighlightStatus(outcome);
  }, [hasChunk, pageNumber, targetPage, chunkText]);

  // Never block modal open on matching: defer to after paint.
  const handleTextLayerRender = useCallback(() => {
    requestAnimationFrame(() => {
      try {
        applyHighlights();
      } catch {
        setHighlightStatus("none"); // page stays displayed regardless
      }
    });
  }, [applyHighlights]);

  const showNote =
    hasChunk && pageNumber === targetPage && highlightStatus !== "pending";

  return (
    <motion.div
      className="fixed inset-0 z-[60] flex items-center justify-center p-3 sm:p-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      role="dialog"
      aria-modal="true"
      aria-label={`${titleCase(source.company)} 10-K, page ${targetPage}`}
    >
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-md"
        onClick={onClose}
      />

      <motion.div
        className="glass-panel light-edge relative flex max-h-full w-full max-w-4xl flex-col overflow-hidden rounded-2xl"
        initial={{ opacity: 0, y: 22, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 14, scale: 0.98 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-3 border-b border-white/[0.06] px-4 py-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-display text-sm font-semibold text-white">
                {titleCase(source.company)}
              </span>
              {source.year != null && (
                <span className="rounded-md bg-accent/15 px-1.5 py-0.5 font-mono text-[11px] text-accent2 ring-1 ring-inset ring-accent/25">
                  FY{source.year}
                </span>
              )}
              <span className="font-mono text-[11px] text-muted">
                p.{targetPage}
              </span>
              {showNote && (
                <HighlightNote outcome={highlightStatus as HighlightOutcome} />
              )}
            </div>
            <p
              className="mt-0.5 truncate font-mono text-[11px] text-muted"
              title={filename}
            >
              {filename}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close viewer"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-white/10 hover:text-ink"
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

        {/* Body */}
        <div
          ref={bodyRef}
          className="no-scrollbar flex min-h-0 flex-1 justify-center overflow-auto bg-black/25 p-4"
        >
          {error ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
              <p className="text-sm text-ink/90">Couldn&apos;t load this filing.</p>
              <p className="max-w-xs text-xs leading-relaxed text-muted">
                Make sure the backend is running on port 8000 and this PDF exists
                in <span className="font-mono">data/pdfs/</span>.
              </p>
              <div className="mt-1 flex items-center gap-2">
                <button
                  type="button"
                  onClick={retry}
                  className="rounded-lg bg-white/10 px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-white/20"
                >
                  Try again
                </button>
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg px-3 py-1.5 text-xs font-medium text-accent2 transition-colors hover:text-white"
                >
                  Open in new tab ↗
                </a>
              </div>
            </div>
          ) : (
            <Document
              key={reloadKey}
              file={url}
              onLoadSuccess={onLoadSuccess}
              onLoadError={(e) =>
                setError(e?.message ?? "Failed to load PDF.")
              }
              loading={<Spinner label="Loading filing…" />}
              error={<span />}
            >
              <div ref={pageWrapRef} className="relative">
                <Page
                  pageNumber={pageNumber}
                  width={pageWidth}
                  renderTextLayer
                  renderAnnotationLayer={false}
                  onRenderTextLayerSuccess={handleTextLayerRender}
                  onRenderTextLayerError={() => setHighlightStatus("none")}
                  loading={<Spinner label={`Rendering page ${pageNumber}…`} />}
                  className="overflow-hidden rounded-lg shadow-[0_10px_40px_-12px_rgba(0,0,0,0.8)]"
                />
              </div>
            </Document>
          )}
        </div>

        {/* Footer / page nav */}
        <div className="flex items-center justify-between gap-3 border-t border-white/[0.06] px-4 py-2.5">
          <NavButton onClick={() => go(-1)} disabled={pageNumber <= 1} dir="prev" />
          <span className="font-mono text-xs text-muted">
            Page {pageNumber}
            {numPages ? ` / ${numPages}` : ""}
          </span>
          <NavButton
            onClick={() => go(1)}
            disabled={numPages != null && pageNumber >= numPages}
            dir="next"
          />
        </div>
      </motion.div>
    </motion.div>
  );
}
