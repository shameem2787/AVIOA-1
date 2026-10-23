# AIVOA.AI — AI-Powered Root Cause Analysis (RCA)

A full-stack prototype for pharmaceutical API manufacturing deviation investigations. It supports PDF/text/email intake, AI-assisted extraction, 5 Whys, fishbone categories, evidence-gap identification, CAPA recommendations, human review, and persistent investigations.

## Features
- React + Redux Toolkit + Vite responsive quality-management UI.
- FastAPI REST API with PDF/text extraction and validation.
- LangGraph pipeline for extraction, investigation, evidence-gap analysis, and CAPA recommendations.
- Groq integration with configurable model. When no key is configured, a deterministic demo mode keeps the workflow usable.
- PostgreSQL via Docker Compose; SQLite fallback for quick local development.
- Editable AI-generated fields; cause status distinguishes hypothesis from reviewer confirmation.
- Sample API deviation report and API documentation.

## Quick start (recommended: Docker)
1. Install Docker Desktop / Docker Engine.
2. Copy `.env.example` to `.env`.
3. Add a newly generated Groq key to `GROQ_API_KEY` (never commit `.env`). If left blank, demo mode works without external AI.
4. Run:
   ```bash
   docker compose up --build
   ```
5. Open http://localhost:5173. API docs: http://localhost:8000/docs.

## Local development without Docker
Backend (Python 3.11+ recommended):
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
# Set GROQ_API_KEY in your environment if you want live AI.
uvicorn app.main:app --reload --port 8000
```
Frontend (Node 20+):
```bash
cd frontend
npm install
npm run dev
```
The frontend defaults to `http://localhost:8000/api`; set `VITE_API_BASE_URL` if needed.

## Main workflow
1. Choose **New investigation**, paste incident text/email or upload a PDF.
2. Select **Analyze with AI**. The backend extracts structured facts and runs the LangGraph analysis.
3. Review/edit the populated deviation fields, 5 Whys, candidate causes, evidence gaps, and CAPA suggestions.
4. Save the investigation. Open **Investigations** to reload saved records.

## API endpoints
- `GET /api/health`
- `GET /api/rca`
- `GET /api/rca/{id}`
- `POST /api/rca/analyze` (multipart file or text/email payload)
- `POST /api/rca` (save new investigation)
- `PUT /api/rca/{id}` (save edits)
- `POST /api/rca/{id}/investigate`
- `POST /api/rca/{id}/capa`
- `POST /api/rca/{id}/review`

## Important prototype limitations
This is an interview/demo prototype, not validated GxP software. Do not use it to make real batch disposition or patient-safety decisions. AI outputs are suggestions and must be reviewed by qualified quality personnel. Production use would require validated intended-use controls, access management, audit-trail controls, electronic-signature assessment, data-integrity validation, retention controls, security review, and applicable regulatory qualification.
