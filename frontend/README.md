# 10-K Intelligence — Frontend

A dark, animated chat UI for the 10-K RAG chatbot. Built with **Next.js (App
Router) + TypeScript + Tailwind + framer-motion**. It talks to the FastAPI
backend over HTTP and streams answers token-by-token.

This folder is fully self-contained and deploys independently (e.g. to Vercel).

## Prerequisites

- Node.js 18.18+ (Node 20/22/24 all work)
- The FastAPI backend running and reachable (default `http://localhost:8000`).
  From the repo root:
  ```bash
  uvicorn backend.main:app --reload --port 8000
  ```
  Make sure at least one config's index is built (e.g.
  `python scripts/build_index.py --config gemini_native`) so questions can be
  answered.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Configuration

The backend base URL is read from `NEXT_PUBLIC_API_URL`, defaulting to
`http://localhost:8000`. To point at a different backend, copy the example env
file and edit it:

```bash
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL=https://your-backend.example.com
```

> When deploying, also set `FRONTEND_ORIGIN` on the **backend** to this app's
> URL so CORS allows the browser requests.

## What it does

- **Streaming chat** against `POST /ask/stream` (SSE), with markdown rendering
  for assistant answers and a live typing effect.
- **Config switcher** populated from `GET /configs`, showing a green dot for
  built indexes and disabling configs whose index isn't built yet (defaults to
  `gemini_native`).
- **Sources panel** that lists the filing excerpts (company, fiscal year, page,
  filename) grounding each answer — a right-hand panel on desktop, a drawer on
  mobile.
- **Handled states**: backend unreachable (friendly banner + retry), a selected
  config with no index (clear inline guidance), empty state with example
  prompts, and per-message error rendering.

## Scripts

| Command         | Description                    |
| --------------- | ------------------------------ |
| `npm run dev`   | Start the dev server (:3000)   |
| `npm run build` | Production build               |
| `npm run start` | Serve the production build     |

## Project structure

```
frontend/
├── app/
│   ├── layout.tsx      # fonts, metadata, root shell
│   ├── page.tsx        # renders <ChatApp/>
│   └── globals.css     # theme, glass/grid/noise utilities
├── components/
│   ├── ChatApp.tsx     # state + orchestration
│   ├── Header.tsx      # brand + tagline + slot
│   ├── ConfigSwitcher.tsx
│   ├── MessageBubble.tsx
│   ├── ChatInput.tsx
│   ├── SourcesPanel.tsx
│   ├── ThinkingIndicator.tsx
│   ├── Markdown.tsx
│   └── Background.tsx  # animated ambient backdrop
└── lib/
    ├── api.ts          # fetchConfigs + streamAsk (SSE parser)
    └── types.ts
```
