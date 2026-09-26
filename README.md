# Project Vigilance

AI-assisted AML investigation platform for the hackathon use case.

## Architecture
React + Vite + TypeScript
FastAPI + Python
PostgreSQL
Polars / NetworkX / scikit-learn
Cytoscape.js

## First milestone
CSV/XLSX ingestion -> validation -> PostgreSQL -> AML detection -> risk score -> investigation UI -> report.

## Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Database
```powershell
docker compose up -d db
```

API: http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs
