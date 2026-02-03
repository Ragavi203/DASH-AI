## AI CSV → Instant Dashboard

Upload any CSV/Excel file → get an auto-generated dashboard (charts, insights, anomalies) + ask questions in natural language.

### Repo layout

- `backend/`: FastAPI + Pandas (profiling, chart suggestions, anomalies, Q&A)
- `frontend/`: Next.js app (upload, dashboard UI, chat, export/share)

### Local dev (quickstart)

#### 1) Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`.

#### 2) Frontend (Next.js)

```bash
cd frontend
npm install
cp env.example .env.local
npm run dev
```

Frontend runs at `http://localhost:3000`.

### Product flow (what to click)

- **Login (recommended)**: open `/login` for passwordless sign-in (enables private history + uploads)
- **Upload**: open the homepage and drag/drop any `.csv` / `.xlsx`
- **Dashboard**: you’ll be routed to `/d/:datasetId` with charts + insights + anomalies + chat
- **Pivot Explorer**: in the Overview tab, run deterministic pivots (group-by + time bucketing) with citations
- **Share**: click “Copy share link” (opens `/s/:shareId`)
- **Export PDF**: click “Export PDF” (hits backend `report.pdf`)
- **Overview**: the executive brief now pairs KPIs with a dataset health score, insight cards (anomalies/correlations/data quality), and chat templates so analysts always know what to ask next.
- **Chat**: recommended prompts live inside the Chat tab; the AI tries to answer anything and falls back to deterministic logic when the model isn’t needed.

### API endpoints (backend)

- `POST /api/auth/request_code`: request a login code (dev returns `dev_code`)
- `POST /api/auth/verify_code`: verify login code → JWT
- `POST /api/datasets/upload`: upload a file, returns `dataset_id`, `share_id`, and `analysis`
- `GET /api/datasets/{dataset_id}`: load stored analysis
- `GET /api/share/{share_id}`: load analysis by share link
- `POST /api/datasets/{dataset_id}/chat`: basic Q&A over the dataset
- `POST /api/datasets/{dataset_id}/pivot`: deterministic slice/pivot (group-by, metric agg, time grain, top-N) with citations
- `GET /api/datasets/{dataset_id}/chat/history`: resume chat history
- `GET /api/datasets/{dataset_id}/anomalies/{anomaly_index}/explain`: explain a spike anomaly (period vs previous + contributors)
- `GET /api/datasets/{dataset_id}/report.pdf`: generate a PDF report

### Tests (backend)

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Optional OpenAI schema eval (only runs if enabled):

```bash
cd backend
source .venv/bin/activate
export RUN_OPENAI_EVALS=1
pytest -q tests/test_openai_schema_optional.py
```

### Migrations (backend, optional)

This repo includes Alembic migrations under `backend/alembic/`.

```bash
cd backend
source .venv/bin/activate
alembic -c alembic.ini upgrade head
```

If you already ran the app previously (SQLite tables created via `create_all`), you may need to stamp the initial migration once:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. alembic -c alembic.ini stamp 20260131_0001
PYTHONPATH=. alembic -c alembic.ini upgrade head
```

### Optional: Postgres + Redis (local)

```bash
docker compose up -d
```

Then set `DATABASE_URL` (backend) to Postgres and restart the API.

### Environment variables

Backend: `backend/env.example`  
Frontend: `frontend/env.example`

Auth (backend):

- `JWT_SECRET`: keep stable; changing it invalidates existing tokens
- `JWT_EXP_MINUTES`: token TTL

### Enable OpenAI for Chat (recommended)

In `backend/.env`:

- `OPENAI_API_KEY`: your key
- `OPENAI_MODEL`: defaults to `gpt-4.1` (override if needed)
- `OPENAI_PROMPT_VERSION`: prompt version string stored in chat citations (helps debugging/evals)
- Budgets:
  - `OPENAI_TIMEOUT_S` (default 25s)
  - `OPENAI_MAX_TOKENS` (default 700)
  - `LLM_MAX_SAMPLE_ROWS` (default 20)
  - `LLM_MAX_COLUMNS` (default 45)

### Privacy / PII (health-data friendly)

On upload, the app runs a lightweight **PII risk scan** (column name + sample value heuristics) and surfaces warnings in the Overview tab.
This is a **best-effort signal**, not a compliance feature.

### Overview & chat highlights

- **Dataset health**: Overview now calculates a 0-100 health score (missing rate + duplicates) with quick notes on high-missing or constant columns.
- **Insight cards**: Analyst-ready takeaways (strong correlations, anomalies, chart mix) are grouped into cards so you can mention them in briefings or share links.
- **Chat templates**: Prompt suggestions appear above the chat input (“top 10 customers by revenue,” “what drove the spike in March?”), and each answer includes citations so you can explain what was computed/determined.
- **Insight automation summary**: Every CSV gets an auto-generated overview narrative plus “what to call out” factor chips (correlations, anomalies, missing columns) so analysts instantly understand what the dataset is about.

### History & audit-friendly workflow

- **Health-first history**: `/history` shows each upload’s health score, missing %, duplicate rows, and insight count so you can focus on clean datasets.
- **Primary metric badge**: Cards surface the executive brief’s key metric and status (ready vs. processing) for quick triage.
- **Audit trail & cleanup**: History links to share/chat/pivot logs, shows request IDs, and deleting a dataset removes uploads, analysis, and chats.

### Auth + private history

History/upload endpoints now require auth. Use `/login` in the frontend (passwordless email code) to get a token.

### Async processing (large files)

Uploads above `UPLOAD_ASYNC_THRESHOLD_BYTES` return immediately with `status=processing`. The dataset page polls until it becomes `ready`.

### Request IDs

Every backend response includes an `x-request-id` header (useful for tracing logs and debugging).

### Senior-analyst features (Overview tab)

- **Executive brief**: primary metric + latest vs previous period change + top drivers (when possible)
- **Data dictionary**: inferred schema, missing %, examples, “id-like”/quality notes
- **Pivot Explorer**: deterministic pivots and time series with citations (no LLM)
- **Data quality & insight cards**: dataset health score, missing/duplicate warnings, and curated insight cards (correlations, anomalies, chart mix) highlight exactly what to call out in a report.

### LLM evaluation

- Golden prompt suite (`tests/golden_prompts/*.json`?) tracks expected outputs + citations; run `pytest` to guard regressions.
- Optional OpenAI schema eval shows the model still respects JSON output; switch `RUN_OPENAI_EVALS=1` for extra validation.
- Each response records `prompt_version`, `model`, `usage`, and `retrieval` metadata so you can compare versions in logs (stored in `ai_events`).

### Retrieval & fine-tuning mindset

- Every chat request starts with deterministic logic (pivot, executive brief, anomalies, health/insight cards) to build the retrieval context that the model actually consumes, effectively making this a lightweight RAG pipeline with structured facts plus citations.
- `ai_events` already records `prompt_version`, `model`, latency, and token usage, so you can roll out a new prompt/model combo, compare costs, and roll back if confidence drops—this is how you run model experimentation safely.
- Analyst signals (e.g., stored chat messages, thumbs-up/down feedback hooks, insight corrections) become the training data you’d feed back into prompt tuning or fine-tuning workflows; think of the dataset health score and insight cards as the guardrails that keep those fine-tuned prompts grounded.

### Observability & monitoring

- Every call logs `x-request-id`, dataset ID, latency, model/usage, and failure reason.
- `ai_events` table stores latency, prompt version, usage, and errors; you can build a dashboard (p95/p99 latency, token cost, error rate) with this data.
- Async jobs (pivot + dataset processing) have progress + status; the UI polls with `status=processing`.
- Add a simple watcher/cron (or connect to your monitoring stack) to alert if `ai_events` latency spikes or job failure rate rises.

### Feedback & human review

- Chat responses expose `citations` so analysts see exactly what was computed.
- You can add thumbs-up/down (future improvement) by saving user feedback in `ChatMessage`.
- PII scan warns about sensitive columns; combine that with a human review workflow or manual override before sharing reports.

### Future improvements (roadmap to senior-analyst excellence)

- Schedule digests or Slack/Teams alerts when dataset health degrades or anomalies are detected (powered by the health score + `ai_events` spikes).
- Let analysts save chat templates (weekly summary, anomaly explainer) and emit them as emails/reports directly from the chat tab.
- Build an observability dashboard that plots `ai_events` latency/cost per prompt version so you can compare GPT-4.1 vs. future models and guard against regressions.
- Extend retention metadata (project, stakeholder, archive flag) so datasets and chats can be archived/purged according to compliance policy.

### Experimentation / A/B testing (future)

- Prompt changes increase `prompt_version` (default `v1` in `.env`); the stored metadata supports comparing metrics across versions.
- You can gate rollout of new prompts, pivot modes, or prompt improvements via feature flags and observe the `ai_events` table for performance gains.
### Deploy (suggested)

- **Frontend**: Vercel (set `NEXT_PUBLIC_API_BASE_URL`)
- **Backend**: Railway / Render (set `DATABASE_URL`, optional `REDIS_URL`, optional LLM key)
- **Storage**: S3 / R2 (future: swap local file storage)


