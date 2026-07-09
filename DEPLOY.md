# Deployment

## Backend → Railway

The FastAPI backend deploys to [Railway](https://railway.app) using Nixpacks.
The repo contains both the Python backend and the Next.js frontend
(`frontend/`); the config below builds **only the backend** — the frontend
deploys separately (e.g. Vercel).

**Configuration files**

| File | Purpose |
|---|---|
| `railway.json` | Nixpacks builder, start command, `/health` healthcheck, watch paths so frontend-only commits don't trigger backend redeploys |
| `.python-version` | Pins Python **3.12** for the Nixpacks build |
| `.railwayignore` | Excludes `frontend/`, `eval/`, local cruft, and all non-production indexes from CLI uploads; ships only `.vectorstore/gemini_native_cs1000_co150` |
| `requirements.txt` | Installed automatically by Nixpacks; chains `backend/requirements.txt` (FastAPI + uvicorn) via `-r` |

**Start command** (from `railway.json` — Railway injects `$PORT` dynamically):

```
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Environment variables to set in the Railway dashboard**

| Variable | Required | Value |
|---|---|---|
| `GOOGLE_API_KEY` | **Yes** | Gemini API key (chat + embeddings). Read from the environment — never committed. |
| `FRONTEND_ORIGIN` | After frontend deploy | The deployed frontend origin, e.g. `https://your-app.vercel.app` (scheme + host, **no trailing slash, no path**). CORS allows this origin plus `http://localhost:3000` for local dev. |

Do **not** set `PORT` — Railway provides it automatically.

**Notes**

- The production FAISS index (`.vectorstore/gemini_native_cs1000_co150`) is
  committed and deploys with the code, so no index build step runs on Railway.
  Only the `gemini_native` config is serveable there (the frontend pins it);
  Ollama-based configs have no local model server in this environment.
- `data/pdfs/` deploys too — the backend serves the filings at
  `/pdfs/{filename}` for the frontend's PDF viewer.
- Verify after deploy: `GET https://<railway-domain>/health` → `{"status":"ok"}`.
- `.railwayignore` applies to CLI (`railway up`) uploads. GitHub-based deploys
  clone the full repo; `watchPatterns` in `railway.json` still keep frontend
  commits from triggering backend rebuilds.

## Frontend → Vercel (for reference)

Deploy `frontend/` with root directory set to `frontend`, and set
`NEXT_PUBLIC_API_URL` to the Railway backend URL (e.g.
`https://<railway-domain>`). Then set `FRONTEND_ORIGIN` on Railway to the
Vercel URL so CORS admits it.
