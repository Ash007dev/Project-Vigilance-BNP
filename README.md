<!-- markdownlint-disable MD001 MD013 MD033 MD041 MD060 -->

<div align="center">

# Project Vigilance

### AI-assisted anti-money-laundering investigation, from raw transactions to an explainable case

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-0.117-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=111827" alt="React 19" />
  <img src="https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL 17" />
  <img src="https://img.shields.io/badge/Graph-NetworkX-7C3AED" alt="NetworkX" />
  <img src="https://img.shields.io/badge/Status-Working%20Prototype-22C55E" alt="Working prototype" />
</p>

**Detect suspicious behaviour. Understand the network. Reconstruct the story.**

[Why it matters](#why-project-vigilance) · [How it works](#how-it-works) · [Quick start](#quick-start) · [API reference](#api-reference) · [Demo flow](#demo-walkthrough)

</div>

---

## Why Project Vigilance?

Financial institutions process enormous transaction volumes across UPI, RTGS, NEFT, IMPS, cards, internet banking, and crypto-linked channels. Traditional AML monitoring often evaluates isolated transactions against fixed rules. That makes coordinated behaviour difficult to see and leaves compliance investigators with noisy alerts, fragmented evidence, and long manual reviews.

Project Vigilance turns transaction data into investigation intelligence. It combines deterministic AML detection, dynamic risk scoring, relationship analysis, chronological evidence, AI-assisted explanations, and downloadable reports in one workflow.

> The platform does not merely say that an account looks suspicious. It shows **why it was flagged, how funds moved, which entities are connected, and what an investigator should review next**.

| Conventional monitoring | Project Vigilance |
|---|---|
| Reviews transactions individually | Reconstructs account and network behaviour |
| Produces threshold-based alerts | Combines multiple AML indicators |
| Requires manual relationship tracing | Builds an interactive relationship graph |
| Gives limited reasoning | Preserves evidence behind every score |
| Scatters investigation artifacts | Brings evidence, timeline, graph, AI, and reporting together |

## How it works

```mermaid
flowchart LR
    A[Upload CSV or XLSX] --> B[Validate and normalize]
    B --> C[(PostgreSQL)]
    C --> D[AML detection engine]
    D --> E[Risk scoring]
    E --> F[Alerts and dashboard]
    F --> G[Investigation workspace]
    G --> H[Transaction timeline]
    G --> I[Relationship graph]
    G --> J[AI explanation]
    G --> K[PDF report]
```

1. **Ingest** — upload a CSV or XLSX transaction dataset.
2. **Validate** — check mandatory fields, normalize types, parse timestamps, and discard invalid required rows.
3. **Detect** — run AML detectors for structuring, layering, circular flow, mule behaviour, shared identifiers, and crypto activity.
4. **Prioritize** — combine evidence into a transparent 0–100 risk score.
5. **Investigate** — review transactions, reasons, relationships, a timeline, and an interactive graph.
6. **Explain** — request a grounded AI summary based on evidence already calculated by the platform.
7. **Report** — export an investigation-ready PDF.

> [!IMPORTANT]
> Uploading a new dataset replaces the currently active dataset. The current prototype does not keep dataset history.

## Core capabilities

| Capability | What it provides |
|---|---|
| Dataset ingestion | CSV/XLSX upload, schema validation, normalization, duplicate reporting, and bulk PostgreSQL insertion |
| AML detection | Six explainable detectors covering transaction, network, and crypto indicators |
| Risk prioritization | Evidence-based scores, severity levels, reasons, and a multiple-pattern bonus |
| Investigation dashboard | Transaction metrics, active alerts, and high-risk prioritization |
| Relationship intelligence | Connected accounts, devices, IP addresses, wallets, and transaction edges |
| Timeline reconstruction | Chronological ordering of relevant financial events |
| Explainable AI | Optional local Ollama explanation constrained to supplied investigation evidence |
| Investigation Copilot | Optional OpenAI-backed, tool-using question endpoint for querying stored transactions |
| PDF reporting | Downloadable investigation summaries with evidence, risk, network, and timeline details |

## AML detection patterns

The detection engine is deterministic: each finding contains a pattern, affected entity, severity, evidence, and a human-readable reason.

| Pattern | What the engine looks for | Current severity |
|---|---|---:|
| Structuring / smurfing | At least three similar sub-threshold transfers from at least three senders to one receiver within 30 minutes | High |
| Mule account | At least three incoming transfers from two or more sources followed by outgoing movement | High |
| Layering | A time-ordered `source → intermediary → destination` chain completed within 30 minutes | High |
| Circular money flow | Directed account cycles containing three to six accounts | Critical |
| Shared device / IP | More than one sender account associated with the same device or IP address | Medium |
| Crypto activity | A crypto flag, wallet value, or crypto-labelled channel associated with a receiver | Medium |

Shared devices, shared IPs, and crypto usage can have legitimate explanations. They are investigation signals—not proof of money laundering. The current crypto detector identifies **crypto exposure**; confirming off-ramping requires additional evidence of conversion to fiat and payout.

## Transparent risk scoring

Risk is calculated from explicit findings rather than generated by an opaque model.

| Finding | Points |
|---|---:|
| Structuring | 30 |
| Mule account | 30 |
| Layering | 25 |
| Circular flow | 35 |
| Shared device | 10 |
| Shared IP | 10 |
| Crypto activity | 10 |
| Two or more independent patterns | +10 bonus |

Scores are capped at 100 and classified as follows:

| Score | Classification |
|---:|---|
| 0–30 | Low |
| 31–60 | Medium |
| 61–80 | High |
| 81–100 | Critical |

The AI layer explains this evidence; it does not determine the final risk score.

## Investigation experience

An alert opens a unified case view containing:

- entity risk score and classification;
- detected AML patterns and scoring reasons;
- related incoming and outgoing transactions;
- connected accounts, devices, IPs, and crypto wallets;
- a chronological activity timeline;
- an interactive Cytoscape relationship graph;
- an on-demand AI explanation; and
- a downloadable PDF investigation report.

The graph distinguishes accounts, devices, IP addresses, wallets, and transactional relationships so an investigator can move from a single alert to the wider financial network.

## System architecture

```mermaid
flowchart TB
    UI[React + TypeScript UI] -->|REST / JSON| API[FastAPI application]

    API --> ING[Ingestion API]
    API --> DET[Detection engine]
    API --> RISK[Risk engine]
    API --> INV[Investigation API]
    API --> GRAPH[Graph builder]
    API --> REPORT[PDF report generator]
    API --> AIX[AI explanation API]
    API --> COPILOT[Copilot API]

    ING --> DB[(PostgreSQL)]
    DET --> DB
    INV --> DB
    GRAPH --> DB
    REPORT --> DB
    RISK --> DET
    AIX --> OLLAMA[Local Ollama model]
    COPILOT --> OPENAI[OpenAI Responses API]
```

The application uses a modular monolith: APIs, detection, risk, graph, AI, and reporting stay separated in code while sharing one FastAPI service and PostgreSQL source of truth. NetworkX performs relationship analysis without requiring a separate graph database.

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, TypeScript, Vite, Axios, Cytoscape.js, Recharts, Lucide React |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Psycopg |
| Data processing | Polars, Pandas |
| Detection and graph | NetworkX, scikit-learn |
| Database | PostgreSQL 17 |
| AI | Ollama (`qwen2.5:1.5b`) and optional OpenAI Responses API |
| Reporting | ReportLab |
| Local infrastructure | Docker Compose |

## Quick start

### Prerequisites

- Git
- Python 3.11+
- Node.js 20+
- npm
- Docker Desktop or Docker Engine with Compose
- Optional: [Ollama](https://ollama.com/) for local AI explanations
- Optional: an OpenAI API key for the backend Copilot endpoint

### 1. Clone the repository

```bash
git clone https://github.com/HEsanthosh/BNP-BLR-Team-17.git
cd BNP-BLR-Team-17
```

### 2. Start PostgreSQL

```bash
docker compose up -d
```

The default development database is available at `localhost:5433` with database, username, and password all set to `vigilance`. The backend's built-in default connection string matches this Docker configuration.

### 3. Start the backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.db.init_db
uvicorn app.main:app --reload
```

For macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

Backend services:

- API: <http://localhost:8000>
- Health check: <http://localhost:8000/health>
- Interactive API docs: <http://localhost:8000/docs>

### 4. Start the frontend

Open a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5174>.

### 5. Enable local AI explanations (optional)

```bash
ollama pull qwen2.5:1.5b
ollama serve
```

The investigation page calls Ollama only when the AI explanation panel is expanded.

### 6. Enable the Copilot API (optional)

Create `.env` in the repository root using `.env.example` as a template:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=your_supported_model
```

Restart FastAPI after changing environment settings. Never commit `.env` or expose API keys in screenshots, logs, or chat.

The Copilot is currently available through `POST /api/copilot/query` and Swagger. A Copilot chat component has not yet been connected to the React interface.

## Dataset contract

### Required columns

| Column | Meaning |
|---|---|
| `transaction_id` | Source transaction identifier |
| `timestamp` | Date and time of the transaction |
| `sender_account` | Originating account |
| `receiver_account` | Destination account |
| `amount` | Transaction amount |

### Optional columns

`sender_customer`, `receiver_customer`, `currency`, `channel`, `ip_address`, `device_id`, `country`, `city`, `crypto_flag`, and `crypto_wallet`.

Example CSV:

```csv
transaction_id,timestamp,sender_account,receiver_account,amount,currency,channel,ip_address,device_id,country,city,crypto_flag,crypto_wallet
TX-001,2026-09-15 10:00:00,ACC-1001,ACC-2001,95000,INR,RTGS,192.168.1.10,DEV-001,IN,Chennai,0,
TX-002,2026-09-15 10:05:00,ACC-1002,ACC-2001,97000,INR,RTGS,192.168.1.10,DEV-001,IN,Chennai,0,
TX-003,2026-09-15 10:10:00,ACC-2001,ACC-3001,180000,INR,IMPS,192.168.1.20,DEV-002,IN,Bengaluru,0,
```

During upload, the backend reports duplicate transaction IDs but does not treat `transaction_id` as the database primary key.

## API reference

Base URL: `http://localhost:8000/api`

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/upload` | Validate and replace the active transaction dataset |
| `GET` | `/stats` | Return transaction, channel, currency, crypto, and network metrics |
| `POST` | `/detect` | Run all AML detectors |
| `GET` | `/risk-scores` | Calculate and return prioritized entity risk scores |
| `GET` | `/alerts` | Return open suspicious-entity alerts |
| `GET` | `/investigations/{account}` | Assemble the complete investigation view |
| `GET` | `/graph/{account}` | Return serialized relationship nodes and edges |
| `GET` | `/ai/explanation/{account}` | Generate an evidence-grounded Ollama explanation |
| `POST` | `/copilot/query` | Ask the OpenAI-backed investigation Copilot a question |
| `GET` | `/report/{account}` | Download an investigation PDF |

Copilot request example:

```json
{
  "question": "Show the largest suspicious transactions and explain the connected accounts."
}
```

## Project structure

```text
BNP-BLR-Team-17/
|-- backend/
|   |-- app/
|   |   |-- api/             # FastAPI route modules
|   |   |-- ai/              # Local AI evidence explainer
|   |   |-- db/              # SQLAlchemy models and database setup
|   |   |-- detection/       # AML detection engine
|   |   |-- graph/           # Relationship graph builder
|   |   |-- ingestion/       # Dataset loading utilities
|   |   |-- risk/            # Risk scoring engine
|   |   `-- main.py          # Application entry point
|   |-- tests/
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |   |-- App.tsx
|   |   |-- Landing.tsx
|   |   |-- Investigation.tsx
|   |   `-- RelationshipGraph.tsx
|   |-- package.json
|   `-- package-lock.json
|-- data/                     # Ignored runtime data directory
|-- reports/                  # Ignored generated-report directory
|-- docker-compose.yml
`-- README.md
```

## Verification

Run backend tests:

```powershell
cd backend
python -m pytest
```

Build the frontend:

```bash
cd frontend
npm run build
```

Useful manual checks:

1. Confirm `/health` returns `status: ok`.
2. Upload a valid CSV from the landing page.
3. Verify dashboard totals and alerts.
4. Open an alert and inspect its evidence, timeline, and graph.
5. Expand the AI explanation if Ollama is running.
6. Export and open the PDF report.

## Demo walkthrough

A focused demonstration can tell the full investigation story in seven steps:

1. **Upload** a prepared transaction dataset.
2. **Validate** the inserted-row count and processing summary.
3. **Prioritize** alerts on the dashboard by risk score.
4. **Investigate** one entity and explain its detected patterns.
5. **Trace** its chronological transaction evidence.
6. **Explore** connected accounts, devices, IPs, and wallets in the graph.
7. **Export** the final investigation report.

Suggested narration:

> Project Vigilance converts raw transactions into an explainable investigation. Deterministic analytics find the risk, the graph reconstructs the network, AI summarizes the evidence, and the report preserves the result for review.

## Design decisions

### Deterministic detection before AI

Risk scores and alerts are calculated from inspectable rules. AI receives the resulting evidence and turns it into investigator-friendly language. This keeps the core decision path reproducible and auditable.

### PostgreSQL plus NetworkX

PostgreSQL remains the transaction source of truth, while NetworkX performs relationship analysis in application code. This keeps the prototype operationally simple without sacrificing graph-based investigation.

### Modular collaboration

Ingestion, detection, risk, graph, AI, reporting, and frontend experiences are separated into focused modules and integrated through FastAPI endpoints. This structure allowed contributors to work independently and merge their work into one consistent investigation flow.

### Investigation support, not automated judgment

Project Vigilance prioritizes cases and explains evidence. A qualified investigator remains responsible for validation, escalation, and final compliance decisions.

## Limitations and responsible use

- Detection rules are heuristics and can produce false positives or miss novel behaviour.
- Current thresholds and risk weights are prototype design choices, not regulatory standards.
- Shared identifiers and crypto activity can have legitimate explanations.
- The crypto detector identifies exposure; it does not independently prove off-ramping.
- AI output can be incomplete or incorrect and must be reviewed against source evidence.
- The current system supports one active dataset rather than versioned datasets and cases.
- Authentication, authorization, audit logging, encryption, and retention controls require production implementation.
- Large transaction tables should use server-side pagination rather than sending every row to the browser.
- Real financial data must be protected according to applicable privacy, security, and AML regulations.

## Troubleshooting

<details>
<summary><strong>PostgreSQL connection fails</strong></summary>

Run `docker compose up -d` and confirm that port `5433` is available. The default backend connection is `postgresql+psycopg://vigilance:vigilance@localhost:5433/vigilance`.

</details>

<details>
<summary><strong>Database tables are missing</strong></summary>

From `backend`, run `python -m app.db.init_db`, then restart FastAPI.

</details>

<details>
<summary><strong>Dataset upload fails</strong></summary>

Confirm that all five required columns exist and that timestamps and amounts are parseable. CSV is recommended for large datasets.

</details>

<details>
<summary><strong>AI explanation cannot connect</strong></summary>

Run `ollama list`, confirm `qwen2.5:1.5b` is installed, and start Ollama with `ollama serve`.

</details>

<details>
<summary><strong>Copilot returns HTTP 503</strong></summary>

Add a valid `OPENAI_API_KEY` to the root `.env` file and restart FastAPI.

</details>

## Roadmap

- Connect the investigation Copilot to the React UI
- Add authentication and role-based access control
- Introduce case ownership, notes, status, and dataset versioning
- Add customer behavioural baselines and configurable thresholds
- Add graph centrality, community detection, and risk propagation
- Add multi-hop money-flow replay
- Add production audit logs, observability, and failure recovery

## Project status

Project Vigilance is a working investigation-support prototype built for demonstration and continued development. Its complete core journey is available today:

```text
Upload -> Detect -> Score -> Alert -> Investigate -> Explain -> Report
```

It must not be used as the sole basis for legal, compliance, or customer-impacting decisions.

---

<div align="center">

**Project Vigilance** — turning transaction data into investigation intelligence.

</div>
