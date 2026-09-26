# Project Vigilance

Project Vigilance is an anti-money-laundering investigation platform. It accepts CSV or Excel transactions, cleans the data, runs 14 detection patterns, scores account risk, builds relationship graphs, creates alerts, and produces investigation reports.

## What is included

| Part | Technology | Purpose |
| --- | --- | --- |
| Web app | React, TypeScript, Vite | Upload, dashboard, alerts, and investigations |
| API | FastAPI, Python | Connects every backend service |
| Ingestion | Polars, pandas, msoffcrypto | Reads, validates, cleans, and quarantines rows |
| Detection | pandas, NetworkX | Finds suspicious transaction behaviour |
| Graph | NetworkX, Cytoscape.js | Shows accounts, devices, IPs, wallets, and transfers |
| Risk | rules and Isolation Forest | Scores accounts from 0 to 100 |
| Reports | Jinja2 and ReportLab | Returns HTML or downloadable PDF reports |
| Database | PostgreSQL and SQLAlchemy | Stores the current clean transaction dataset |

## Architecture

```mermaid
flowchart LR
    U[Investigator] --> UI[React web app]
    UI --> API[FastAPI API]

    X[CSV or encrypted Excel] --> ING[Ingestion pipeline]
    API --> ING
    ING -->|clean rows| DB[(PostgreSQL)]
    ING -->|invalid rows| Q[Quarantine result]

    DB --> DET[14 AML detectors]
    DB --> GRAPH[Relationship graph]
    DET --> RISK[Risk scoring]
    RISK --> ALERTS[Alerts]

    API --> DET
    API --> GRAPH
    API --> RISK
    API --> ALERTS
    ALERTS --> INV[Investigation view]
    GRAPH --> INV
    INV --> REPORT[HTML or PDF report]
    REPORT --> API
```

The graph is built once for a complete detection run. Each detector receives the DataFrame, the graph, or both, depending on what it needs.

## Detection patterns

| Pattern | What it finds |
| --- | --- |
| Structuring | Many smaller transfers that may avoid a reporting limit |
| Layering | Money moving through several connected accounts in a short period |
| Circular flow | Funds returning to an earlier account in a transaction cycle |
| Mule behaviour | Accounts that quickly receive and forward money |
| Shared device or IP | Different accounts using the same device or network address |
| Crypto off-ramp | Suspicious movement involving crypto channels or wallets |
| Fan-in or fan-out | Many accounts paying one account, or one account paying many |
| Dormant reactivation | A quiet account becoming active with unusual transfers |
| Threshold avoidance | Values repeatedly kept just below a configured limit |
| Bridge nodes | An account connecting otherwise separate groups |
| Off-hours anomaly | Activity at unusual hours compared with normal behaviour |
| Cross-channel hopping | Money moving through several payment channels |
| Round tripping | Funds sent out and returned through related transfers |
| Behavioural clustering | Accounts with unusually similar transaction behaviour |

Every finding has the same basic shape: account, pattern, and evidence. This keeps risk, alerts, investigations, and tests consistent.

## API

The interactive API documentation is available at `http://127.0.0.1:8000/docs` after the backend starts.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Basic service information |
| `GET` | `/health` | Health check |
| `POST` | `/api/upload` | Clean a CSV/XLS/XLSX file and replace stored transactions |
| `GET` | `/api/stats` | Dataset, currency, channel, crypto, and network totals |
| `POST` | `/api/detect` | Run all 14 detectors |
| `GET` | `/api/risk-scores` | Calculate account risk scores |
| `GET` | `/api/alerts` | Return non-low-risk alerts |
| `GET` | `/api/investigations/{account}` | Return evidence, timeline, transactions, and relationships |
| `GET` | `/api/graph/{account}` | Return a Cytoscape-ready relationship graph |
| `POST` | `/api/reports/overview` | Build an overview report from a supplied payload |
| `POST` | `/api/reports/flagged-cases` | Build a flagged-cases report from a supplied payload |
| `POST` | `/api/reports/investigation` | Build an investigation report from a supplied payload |
| `GET` | `/api/reports/flagged-cases` | Build a report from current risk results |
| `GET` | `/api/reports/investigation/{account}` | Build a report from a current investigation |

Report endpoints accept `?format=pdf` by default. Use `?format=html` to preview a report in the browser. The live flagged-cases report also accepts `min_risk_score` from 0 to 100.

## Run the project

### Requirements

- Python 3.11 or newer
- Node.js 20.19 or newer
- Docker Desktop, or a local PostgreSQL server

### 1. Start PostgreSQL

From the project root:

```powershell
docker compose up -d db
```

The included database runs on host port `5433`.

### 2. Start the backend

Open a PowerShell terminal from the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://vigilance:vigilance@localhost:5433/vigilance"
python -m app.db.init_db
uvicorn app.main:app --reload --port 8000
```

Backend: `http://127.0.0.1:8000`

API docs: `http://127.0.0.1:8000/docs`

### 3. Start the frontend

Open a second PowerShell terminal from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Web app: `http://127.0.0.1:5174`

### 4. Load data

Upload a `.csv`, `.xls`, or `.xlsx` file from the web app or the `/api/upload` endpoint. A successful upload replaces the current contents of the `transactions` table.

For the password-protected project workbook, set `VIGILANCE_DATASET_PASSWORD` only in your local terminal before starting the API or dataset tests. Do not put the password in source code, README files, commits, or screenshots.

## Tests

Install test tools, then run the normal suite from the project root:

```powershell
python -m pip install -r backend/requirements-dev.txt
python -m pytest -q
```

Dataset tests are skipped unless the workbook password is available:

```powershell
$env:VIGILANCE_DATASET_PASSWORD = "<your-local-workbook-password>"
python -m pytest -m dataset -q
Remove-Item Env:VIGILANCE_DATASET_PASSWORD
```

Build the web app for production:

```powershell
cd frontend
npm run build
```

## Project layout

```text
backend/
  app/
    api/          FastAPI routes
    db/           database connection and models
    detection/    detector registry and 14 detectors
    graph/        graph builders, algorithms, and serializers
    ingestion/    loading, cleaning, validation, and quarantine
    reports/      report schemas, templates, and PDF generation
    risk/         features, rules, model, and scoring
  tests/          backend and real-dataset integration tests
frontend/
  src/            React pages, components, graph, and styles
data/             local data area; generated data is ignored
reports/          local report output area
docker-compose.yml
pytest.ini
```

## Useful commands

| Task | Command |
| --- | --- |
| Stop the database | `docker compose down` |
| View database logs | `docker compose logs -f db` |
| Recreate missing tables | `cd backend; python -m app.db.init_db` |
| Run only report tests | `python -m pytest backend/tests/test_reports_api.py -q` |
| Compile-check Python | `python -m compileall -q backend/app backend/tests` |
| Check the frontend build | `cd frontend; npm run build` |

If the API cannot connect to PostgreSQL, confirm Docker is running and that `DATABASE_URL` uses port `5433`, not the container's internal port `5432`.
