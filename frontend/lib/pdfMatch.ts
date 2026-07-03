// Defensive, best-effort matching of a retrieved chunk's text against a PDF
// page's text-layer spans. Everything here is pure and never throws on bad
// input; if nothing matches, callers simply highlight nothing.

export type HighlightOutcome = "full" | "partial" | "none";

/** Collapse whitespace, normalize quotes/dashes, lowercase (for matching only). */
export function normalize(s: string): string {
  return (s || "")
    .replace(/[‘’‛′]/g, "'") // curly single quotes
    .replace(/[“”‟″]/g, '"') // curly double quotes
    .replace(/[‐-―−]/g, "-") // dashes / minus
    .replace(/ /g, " ") // nbsp
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

/** Sentence-ish fragments, WITHOUT regex lookbehind (Safari-safe). */
export function splitFragments(s: string): string[] {
  return s
    .split(/[.?!;:]\s+/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function firstWindow(words: string[], k: number, hay: string): string | null {
  for (let i = 0; i + k <= words.length; i++) {
    const w = words.slice(i, i + k).join(" ");
    if (hay.includes(w)) return w;
  }
  return null;
}

/**
 * Longest run of consecutive words from `words` that appears verbatim in `hay`.
 * Binary search on run length (monotonic: if a size-k run matches, some size
 * k-1 run also matches, since it's a substring).
 */
export function longestContiguous(words: string[], hay: string): string {
  let lo = 1;
  let hi = words.length;
  let best = "";
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const w = firstWindow(words, mid, hay);
    if (w !== null) {
      best = w;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return best;
}

/**
 * Find which of the page's text-layer spans should be highlighted for a chunk.
 * Generic over the element type so it can be unit-tested with plain objects.
 *
 * Fallback ladder:
 *   1. normalize both sides
 *   2. longest contiguous run of the chunk present on the page
 *   3. sentence-level fragments that appear on the page
 *   4. nothing → highlight nothing (outcome "none")
 */
export function computeMatchedSpans<T extends { textContent: string | null }>(
  spanEls: T[],
  chunkText: string,
): { matched: T[]; outcome: HighlightOutcome } {
  const chunkNorm = normalize(chunkText);
  if (!chunkNorm) return { matched: [], outcome: "none" };

  // Reconstruct normalized page text; record each span's char range within it.
  let pageNorm = "";
  const ranges: { el: T; start: number; end: number }[] = [];
  for (const el of spanEls) {
    const norm = normalize(el.textContent || "");
    if (!norm) {
      ranges.push({ el, start: pageNorm.length, end: pageNorm.length });
      continue;
    }
    if (pageNorm.length) pageNorm += " ";
    const start = pageNorm.length;
    pageNorm += norm;
    ranges.push({ el, start, end: pageNorm.length });
  }
  if (!pageNorm) return { matched: [], outcome: "none" };

  const intervals: [number, number][] = [];
  let matchedChars = 0;
  const addInterval = (start: number, len: number) => {
    if (start < 0 || len <= 0) return;
    const end = start + len;
    if (intervals.some(([s, e]) => start < e && end > s)) return; // overlap
    intervals.push([start, end]);
    matchedChars += len;
  };

  // (1)+(2) longest contiguous run on this page.
  const words = chunkNorm.split(" ").filter(Boolean);
  const best = longestContiguous(words, pageNorm);
  if (best && best.split(" ").length >= 4) {
    addInterval(pageNorm.indexOf(best), best.length);
  }

  // (3) sentence-level fragments.
  for (const frag of splitFragments(chunkNorm)) {
    if (frag.length < 14 || frag.split(" ").length < 4) continue;
    const idx = pageNorm.indexOf(frag);
    if (idx >= 0) addInterval(idx, frag.length);
  }

  if (!intervals.length) return { matched: [], outcome: "none" };

  const matched = ranges
    .filter(
      (r) =>
        r.end > r.start && intervals.some(([s, e]) => r.start < e && r.end > s),
    )
    .map((r) => r.el);

  const coverage = matchedChars / chunkNorm.length;
  return { matched, outcome: coverage >= 0.5 ? "full" : "partial" };
}
