"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Assistant answers arrive as markdown. Render with GFM (tables, lists) and a
 * restrained dark prose theme tuned to the app's palette.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div
      className="md-body prose prose-invert max-w-none
        prose-headings:font-display prose-headings:text-white prose-headings:font-semibold
        prose-p:text-ink/90
        prose-strong:text-white prose-strong:font-semibold
        prose-a:text-accent2 prose-a:no-underline hover:prose-a:underline
        prose-li:text-ink/90 prose-li:my-0.5
        prose-ul:my-2 prose-ol:my-2
        prose-code:text-accent2 prose-code:before:content-none prose-code:after:content-none
        prose-code:rounded prose-code:bg-white/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[0.85em]
        prose-blockquote:border-l-accent/50 prose-blockquote:text-muted
        prose-hr:border-line
        prose-th:text-white prose-td:text-ink/85
        marker:text-accent"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
