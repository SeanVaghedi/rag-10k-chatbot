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

// A thousands-separated figure, optionally $-prefixed, optional decimals.
// Requires at least one comma group so we don't pick up years / small counts.
const NUMBER_PATTERN = String.raw`\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?`;

/** Bare digits + decimal point (drops "$", commas, spaces): "$82,312" -> "82312". */
function normNumber(token: string): string {
  return token.replace(/[^\d.]/g, "");
}

/**
 * Distinctive numeric figures from `text`, normalized. Only thousands-separated
 * numbers (>= 4 digits) are kept, so years like "2024" and small counts are
 * ignored — this targets dense financial-table figures like "$82,312".
 */
export function extractDistinctiveNumbers(text: string): Set<string> {
  const out = new Set<string>();
  if (!text) return out;
  const re = new RegExp(NUMBER_PATTERN, "g");
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const norm = normNumber(m[0]);
    if (norm.replace(/\./g, "").length >= 4) out.add(norm);
  }
  return out;
}

/**
 * Spans that contain a *whole* number token equal to one of `numbers`. Compared
 * as normalized figures, so "$82,312" == "82,312". Whole-token comparison avoids
 * substring false positives (e.g. "1,082,312" does not match "82,312").
 */
export function numericMatchedSpans<T extends { textContent: string | null }>(
  spanEls: T[],
  numbers: Set<string>,
): T[] {
  const out: T[] = [];
  if (numbers.size === 0) return out;
  for (const el of spanEls) {
    const text = el.textContent || "";
    const re = new RegExp(NUMBER_PATTERN, "g");
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      if (numbers.has(normNumber(m[0]))) {
        out.push(el);
        break;
      }
    }
  }
  return out;
}

/**
 * Find which of the page's text-layer spans should be highlighted for a chunk.
 * Generic over the element type so it can be unit-tested with plain objects.
 *
 * Two passes, unioned:
 *   A. Prose: normalize both sides → longest contiguous run → sentence fragments.
 *   B. Numeric: distinctive figures from the chunk, matched anywhere on the page
 *      (catches specific table numbers even when the surrounding prose order is
 *      scrambled). The same number may legitimately appear more than once on a
 *      page (e.g. year-end == next-year beginning balance); all are highlighted.
 * If nothing matches, outcome is "none" and the page still shows normally.
 */
export function computeMatchedSpans<T extends { textContent: string | null }>(
  spanEls: T[],
  chunkText: string,
): { matched: T[]; outcome: HighlightOutcome } {
  const chunkNorm = normalize(chunkText);

  // ---- Pass A: prose / fragment matching -----------------------------------
  const proseMatched: T[] = [];
  let proseOutcome: HighlightOutcome = "none";
  if (chunkNorm) {
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

    if (pageNorm) {
      const intervals: [number, number][] = [];
      let matchedChars = 0;
      const addInterval = (start: number, len: number) => {
        if (start < 0 || len <= 0) return;
        const end = start + len;
        if (intervals.some(([s, e]) => start < e && end > s)) return; // overlap
        intervals.push([start, end]);
        matchedChars += len;
      };

      const words = chunkNorm.split(" ").filter(Boolean);
      const best = longestContiguous(words, pageNorm);
      if (best && best.split(" ").length >= 4) {
        addInterval(pageNorm.indexOf(best), best.length);
      }
      for (const frag of splitFragments(chunkNorm)) {
        if (frag.length < 14 || frag.split(" ").length < 4) continue;
        const idx = pageNorm.indexOf(frag);
        if (idx >= 0) addInterval(idx, frag.length);
      }

      if (intervals.length) {
        for (const r of ranges) {
          if (
            r.end > r.start &&
            intervals.some(([s, e]) => r.start < e && r.end > s)
          ) {
            proseMatched.push(r.el);
          }
        }
        const coverage = matchedChars / chunkNorm.length;
        proseOutcome = coverage >= 0.5 ? "full" : "partial";
      }
    }
  }

  // ---- Pass B: supplemental numeric-figure matching ------------------------
  const numericMatched = numericMatchedSpans(
    spanEls,
    extractDistinctiveNumbers(chunkText),
  );

  // ---- Union (prose first, then numeric spans not already included) --------
  const seen = new Set<T>(proseMatched);
  const matched = [...proseMatched];
  for (const el of numericMatched) {
    if (!seen.has(el)) {
      seen.add(el);
      matched.push(el);
    }
  }

  let outcome: HighlightOutcome;
  if (matched.length === 0) outcome = "none";
  else if (proseOutcome === "full") outcome = "full";
  else outcome = "partial";

  return { matched, outcome };
}
