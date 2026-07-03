import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Deliberate pairing: a characterful contemporary grotesque for display, a
// neutral highly-legible sans for body, and a mono for data/labels.
const display = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});
const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});
const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "10-K Intelligence — Alphabet · Amazon · Microsoft",
  description:
    "A retrieval-augmented AI that answers grounded questions across the annual 10-K filings of Alphabet, Amazon, and Microsoft.",
};

export const viewport: Viewport = {
  themeColor: "#06070e",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${sans.variable} ${mono.variable}`}
    >
      <body className="min-h-[100dvh] bg-bg font-sans text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
