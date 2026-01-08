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

- **Upload**: open the homepage and drag/drop any `.csv` / `.xlsx`
- **Dashboard**: you’ll be routed to `/d/:datasetId` with charts + insights + anomalies + chat
- **Share**: click “Copy share link” (opens `/s/:shareId`)
- **Export PDF**: click “Export PDF” (hits backend `report.pdf`)

### API endpoints (backend)

- `POST /api/datasets/upload`: upload a file, returns `dataset_id`, `share_id`, and `analysis`
- `GET /api/datasets/{dataset_id}`: load stored analysis
- `GET /api/share/{share_id}`: load analysis by share link
- `POST /api/datasets/{dataset_id}/chat`: basic Q&A over the dataset
- `GET /api/datasets/{dataset_id}/report.pdf`: generate a PDF report

### Optional: Postgres + Redis (local)

```bash
docker compose up -d
```

Then set `DATABASE_URL` (backend) to Postgres and restart the API.

### Environment variables

Backend: `backend/env.example`  
Frontend: `frontend/env.example`

### Enable OpenAI for Chat (recommended)

In `backend/.env`:

- `OPENAI_API_KEY`: your key
- `OPENAI_MODEL`: defaults to `gpt-4.1` (override if needed)

### Deploy (suggested)

- **Frontend**: Vercel (set `NEXT_PUBLIC_API_BASE_URL`)
- **Backend**: Railway / Render (set `DATABASE_URL`, optional `REDIS_URL`, optional LLM key)
- **Storage**: S3 / R2 (future: swap local file storage)


