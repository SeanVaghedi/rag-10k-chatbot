// Copies the pdf.js worker into public/ so it is served as a static asset.
// react-pdf 7 / pdfjs-dist 3 ship a classic (.js) worker that Next.js 14's
// webpack handles without the ESM (.mjs) bundling errors. Version-locked to the
// installed pdfjs-dist. Resilient: never fails an install/uninstall.
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

try {
  const require = createRequire(import.meta.url);
  const pkgDir = dirname(require.resolve("pdfjs-dist/package.json"));
  const workerSrc = join(pkgDir, "build", "pdf.worker.min.js");
  mkdirSync("public", { recursive: true });
  copyFileSync(workerSrc, join("public", "pdf.worker.min.js"));
  console.log("Copied pdf.worker.min.js -> public/pdf.worker.min.js");
} catch (err) {
  console.warn("[copy-pdf-worker] skipped:", err.message);
}
