# SkillPilot frontend

React + TypeScript + Vite + Tailwind CSS v4 + React Router. Talks only to the FastAPI backend.

## Run locally

Backend (from the repository root, with your virtualenv active and PostgreSQL + Ollama running):

    uvicorn app.main:app --reload --port 8000

Frontend (from `frontend/`):

    npm install
    cp .env.example .env.local     # edit if your backend is not at http://localhost:8000
    npm run dev                    # http://localhost:5173

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | frontend (build time) | Backend address. Default `http://localhost:8000`. Public: never put secrets here. |
| `CORS_ALLOWED_ORIGINS` | backend `.env` | JSON list of browser origins allowed to call the API. Default: `http://localhost:5173` and `http://127.0.0.1:5173`. |

## Structure

    src/api/        client.ts (base URL, timeouts, error mapping), types.ts, guards.ts (runtime response checks), tutor.ts, roadmap.ts
    src/components/ AppShell (sidebar / mobile nav), ui.tsx (Button, Alert, Dialog, Field, Spinner, EmptyState),
                    RoadmapView (timeline), GenerateForm, RevisePanel
    src/pages/      TutorPage, RoadmapPage

## Endpoints used

| Endpoint | Where |
|---|---|
| `GET /tutor/history?conversation_id&limit` | Tutor: load conversation (limit 100) |
| `POST /tutor/ask` | Tutor: send a question |
| `GET /roadmap/list` | Roadmap: list and default selection (newest first) |
| `GET /roadmap/{id}` | Roadmap: open one roadmap |
| `POST /roadmap/generate` | Generate form (saves a new roadmap, behind a confirmation) |
| `POST /roadmap/revise` | Revision proposal (nothing saved) |
| `POST /roadmap/{id}/accept-revision` | Accept proposal (overwrites, behind a confirmation) |

Not used: `GET /roadmap` (always equals the first item of `/roadmap/list`), `POST /roadmap` (manual create), `/students*`, `/`, `/health`.

## Build and deploy

    npm run build      # output: frontend/dist (static files)

Set `VITE_API_BASE_URL` to the deployed backend URL **when building** (Vite inlines it), and add the deployed frontend origin to the backend's `CORS_ALLOWED_ORIGINS`. Any static host works. Because the app uses client-side routes (`/tutor`, `/roadmap`), configure the host to serve `index.html` for unknown paths.

### Why the backend is not cloud-ready as is
- **PostgreSQL with the `pgvector` extension** is required (tutor embeddings, roadmaps). Needs a managed Postgres that supports pgvector.
- **Ollama** is required by the Tutor (chat model `ollama_model`) and by embeddings (`OllamaEmbeddings`); the code has no alternative provider for these. Needs a GPU/CPU host running Ollama, or code changes to use a hosted LLM.
- **Reranker**: `sentence_transformers.CrossEncoder` downloads and runs a model inside the API process (heavy RAM, slow cold start).
- **Roadmap** can use NVIDIA NIM (`ROADMAP_LLM_PROVIDER=nvidia`, needs `NVIDIA_API_KEY`) or Ollama.
- **No authentication**: a fixed student ID is hard-coded, and all data is shared by anyone who can reach the API. Do not expose it publicly as is.
