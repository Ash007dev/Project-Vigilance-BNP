# Project Vigilance

## AI-Assisted Anti-Money-Laundering Investigation Platform

> Project Vigilance is a web-based AML investigation platform designed to help investigators move from raw transaction data to explainable suspicious-activity investigations, relationship analysis, timelines, risk assessment, AI-assisted explanations, and downloadable investigation reports.

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Objectives](#objectives)
- [End-to-End Workflow](#end-to-end-workflow)
- [Key Features](#key-features)
- [AML Detection Patterns](#aml-detection-patterns)
- [Risk Scoring](#risk-scoring)
- [Explainable AI](#explainable-ai)
- [Investigation Graph](#investigation-graph)
- [Investigation Timeline](#investigation-timeline)
- [Investigation Reports](#investigation-reports)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
- [Dataset Requirements](#dataset-requirements)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [First-Time Usage](#first-time-usage)
- [API Reference](#api-reference)
- [Large Dataset Considerations](#large-dataset-considerations)
- [Troubleshooting](#troubleshooting)
- [Development Workflow](#development-workflow)
- [Testing Checklist](#testing-checklist)
- [Design Decisions](#design-decisions)
- [Limitations](#limitations)
- [Security and Responsible Use](#security-and-responsible-use)
- [Future Enhancements](#future-enhancements)
- [Demo Walkthrough](#demo-walkthrough)
- [Project Status](#project-status)
- [License](#license)

---

# Overview

Project Vigilance is an AI-assisted Anti-Money-Laundering investigation platform.

The central idea is simple:

> **Do not only tell an investigator that something is suspicious. Help the investigator understand why it is suspicious, how the money moved, what entities are connected, and what evidence should be reviewed.**

The platform combines transaction processing, rule-based AML detection, risk scoring, relationship/network analysis, timeline reconstruction, explainability, optional local generative AI, and downloadable investigation reports in one workflow.

The implementation is aligned with the supplied Project Vigilance use case, whose required flow is dataset ingestion → suspicious-activity detection → risk score/classification → alert → investigation dashboard → relationship graph → timeline → AI explanation → investigation report. fileciteturn21file0

---

# Problem Statement

Financial institutions process very large numbers of transactions across channels such as internet banking, UPI, RTGS, NEFT, IMPS, cards and other payment systems. Suspicious behaviour can involve transaction splitting, multiple intermediary accounts, circular movement, mule accounts, shared devices/IPs and cryptocurrency activity.

Looking at individual transactions in isolation can make these relationships difficult to understand. Project Vigilance therefore focuses on reconstructing the broader financial-activity story and giving investigators usable evidence rather than only producing isolated alerts.

The original use case explicitly calls for upload and processing of transaction datasets, suspicious-account/network identification, AML pattern detection, risk scoring, explainability, interactive relationship visualization, investigation search/exploration, dashboards and downloadable reports. fileciteturn21file1turn21file2

---

# Objectives

Project Vigilance aims to:

1. Upload transaction datasets.
2. Validate and normalize transaction data.
3. Store transaction records in PostgreSQL.
4. Detect common AML patterns.
5. Calculate explainable risk scores from 0–100.
6. Classify entities into Low, Medium, High or Critical risk.
7. Generate investigation alerts.
8. Explore suspicious entities through a relationship graph.
9. Trace transactions chronologically.
10. Present supporting transaction evidence.
11. Explain risk indicators in human-readable language.
12. Provide optional AI-assisted investigation explanations.
13. Generate downloadable investigation reports.
14. Demonstrate a complete end-to-end investigation workflow.

The supplied use case specifically defines risk scoring, explainability, relationship visualization, dashboard analytics and reporting as core capabilities. fileciteturn21file2

---

# End-to-End Workflow

```text
                         PROJECT VIGILANCE
                                |
                                v
                    +-----------------------+
                    | Landing / Upload      |
                    | CSV / XLSX            |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Data Validation       |
                    | Cleaning / Normalize  |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | PostgreSQL            |
                    | Transaction Store     |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | AML Detection Engine  |
                    +-----------+-----------+
                                |
              +-----------------+------------------+
              |                 |                  |
              v                 v                  v
        Structuring        Layering          Mule Accounts
              |                 |                  |
              +-----------------+------------------+
                                |
                                v
                    +-----------------------+
                    | Risk Scoring           |
                    | 0 - 100                |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Alerts                 |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Investigation View     |
                    +-----------+-----------+
                                |
             +------------------+------------------+
             |                  |                  |
             v                  v                  v
       Transactions          Timeline           Graph
             |                  |                  |
             +------------------+------------------+
                                |
                                v
                    +-----------------------+
                    | AI Explanation         |
                    | Optional / On Demand   |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    | Investigation Report   |
                    | PDF                    |
                    +-----------------------+
```

This mirrors the integration flow required by the use case. fileciteturn21file0

---

# Key Features

## Automated Dataset Upload

The landing experience supports automated analysis by allowing an investigator to upload a transaction dataset.

Supported formats:

- `.csv`
- `.xlsx`

For the large AML dataset, CSV is recommended because the current ingestion pipeline uses Polars directly for CSV and the large dataset is more practical to process in CSV form.

## Data Validation

The backend validates mandatory fields, normalizes data types, parses timestamps, fills absent optional fields, removes invalid mandatory rows, detects duplicate transaction IDs and loads the valid records into PostgreSQL.

## AML Detection

The detection engine currently covers:

- Structuring / Smurfing
- Layering
- Circular Money Flow
- Mule Account Behaviour
- Shared Device Behaviour
- Shared IP Behaviour
- Crypto Activity / Off-Ramping

The supplied use case requires at least four AML patterns and lists these categories as the expected detection scenarios. fileciteturn21file0

## Dashboard

The dashboard presents dataset and alert information including transaction counts, amounts, currencies, channels, crypto activity, network indicators and risk/alert counts.

## Investigation View

An alert can be opened as an investigation. The investigation view brings together risk, patterns, transaction evidence, timeline, relationships and graph analysis.

## Relationship Graph

The graph makes relationships between accounts, devices, IP addresses and transactions visually understandable.

## AI-Assisted Explanation

The optional local AI layer generates a human-readable explanation from evidence already calculated by the application.

## PDF Investigation Report

The investigator can export a structured PDF containing risk information, patterns, evidence, relationships, timeline, analyst observations, recommended investigation actions and a disclaimer.

The original use case requires a meaningful downloadable investigation report containing transaction details, AI risk information, investigation summary, evidence, analyst observations and recommended actions. fileciteturn21file0

---

# AML Detection Patterns

## Structuring / Smurfing

Structuring refers to splitting larger amounts into multiple smaller transactions. Project Vigilance searches for concentrated transaction activity involving multiple senders, short time windows, repeated transactions and amount patterns around the configured detection logic.

## Layering

Layering involves moving funds through intermediary accounts. The current implementation looks for multi-step transaction paths and uses transaction timing to distinguish actual movement sequences from unrelated graph edges.

Example:

```text
A -> B -> C
```

## Circular Money Flow

Circular detection searches for transaction cycles such as:

```text
A -> B
B -> C
C -> A
```

Graph traversal is used to discover closed transaction paths.

## Mule Account Behaviour

The mule detector considers accounts receiving funds and subsequently forwarding funds. The implementation examines incoming/outgoing activity, sources, destinations and transaction timing.

## Shared Device Behaviour

Multiple accounts associated with the same device are treated as a network indicator for investigation.

## Shared IP Behaviour

Multiple accounts associated with the same IP address are treated as another relationship indicator.

## Crypto Activity

Crypto-related transactions are identified using crypto flags, crypto wallet information and crypto-related channel information.

These indicators are evidence for investigation and should not be interpreted individually as proof of wrongdoing.

---

# Risk Scoring

Project Vigilance currently uses an explainable deterministic scoring layer.

Current prototype pattern contributions are:

| Pattern | Points |
|---|---:|
| STRUCTURING | +30 |
| MULE_ACCOUNT | +30 |
| LAYERING | +25 |
| CIRCULAR_FLOW | +35 |
| SHARED_DEVICE | +10 |
| SHARED_IP | +10 |
| CRYPTO_ACTIVITY | +10 |

When multiple independent patterns are detected for an entity, an additional multiple-pattern contribution is applied. The final score is capped at 100.

Risk classification:

| Score | Classification |
|---:|---|
| 0–30 | LOW |
| 31–60 | MEDIUM |
| 61–80 | HIGH |
| 81–100 | CRITICAL |

These weights are prototype implementation choices and are not presented as regulatory thresholds.

The use case requires a 0–100 risk score and the Low/Medium/High/Critical classification model. fileciteturn21file2

---

# Explainable AI

Project Vigilance separates deterministic evidence from generative explanation.

```text
Transactions
     |
     v
Detection Engine
     |
     v
Risk Engine
     |
     v
Evidence Package
     |
     v
AI Explainer
     |
     v
Human-readable explanation
```

The AI does **not** independently determine the final risk score. It receives evidence such as:

- investigated entity
- risk score
- risk classification
- detected patterns
- transaction evidence
- network information
- timeline information

and turns that evidence into a natural-language explanation.

This design is consistent with the intended role of AI as investigator decision support rather than a final compliance decision-maker. fileciteturn21file0

The AI interface is intentionally designed to be collapsed/on-demand. Local model inference can take time, so investigators can first review the deterministic risk, graph, evidence and timeline and expand AI explanation when required.

---

# Investigation Graph

The graph is built from transaction relationships and supporting entity relationships.

Conceptually:

```text
                 Account A
                     |
                     |
Account B -------- Target -------- Account C
                     |
                     |
                 Account D
                     |
                 Device X
                     |
                  IP X
```

Possible node types:

```text
ACCOUNT
DEVICE
IP
WALLET
```

Possible relationship types include:

```text
TRANSACTION
SHARED_DEVICE
SHARED_IP
CRYPTO
```

The backend uses NetworkX for relationship analysis and the frontend uses Cytoscape.js/react-cytoscapejs for visualization.

The graph is intended to help investigators trace multi-hop relationships and identify connected entities, as required by the investigation visualization portion of the use case. fileciteturn21file0

---

# Investigation Timeline

Transactions associated with an investigated entity are displayed chronologically.

Example:

```text
10:00:02   A -> B   95,000
10:04:17   B -> C   91,000
10:08:31   C -> D   89,500
10:11:42   D -> E   87,000
```

The timeline helps investigators understand:

- transaction order
- transaction velocity
- movement through intermediary accounts
- concentration of suspicious activity
- relationships between detected patterns and actual events

---

# Investigation Reports

Project Vigilance generates a downloadable PDF investigation report using ReportLab.

The report contains structured sections such as:

1. Report metadata
2. Executive summary
3. Risk assessment
4. Detected AML patterns
5. Investigation evidence and reasons
6. Relationship/network evidence
7. Transaction evidence
8. Investigation timeline
9. Analyst observations
10. Recommended investigation actions
11. AI-assisted analysis information
12. Disclaimer

The report is designed as an investigation artifact rather than a raw transaction export.

---

# System Architecture

```text
                         +---------------------+
                         |       Browser       |
                         | React + TypeScript  |
                         +----------+----------+
                                    |
                                  HTTP
                                    |
                                    v
                         +---------------------+
                         |       FastAPI       |
                         |      REST APIs      |
                         +----------+----------+
                                    |
              +---------------------+---------------------+
              |                     |                     |
              v                     v                     v
       +--------------+      +--------------+      +--------------+
       | Detection    |      | Risk Engine  |      | AI Explainer |
       | Engine       |      |              |      | Ollama       |
       +------+-------+      +------+-------+      +--------------+
              |                     |
              +----------+----------+
                         |
                         v
                +------------------+
                |   PostgreSQL     |
                |   Transactions   |
                +------------------+
```

The architecture intentionally keeps the system modular without introducing unnecessary microservices or infrastructure for the core workflow.

---

# Technology Stack

## Frontend

| Technology | Purpose |
|---|---|
| React | UI framework |
| TypeScript | Type-safe frontend |
| Vite | Development/build tooling |
| Axios | HTTP communication |
| Recharts | Dashboard charts |
| Cytoscape.js | Relationship graph |
| react-cytoscapejs | React graph integration |
| Lucide React | UI icons |
| CSS | Application styling |

## Backend

| Technology | Purpose |
|---|---|
| Python | Backend language |
| FastAPI | REST API framework |
| Polars | Dataset ingestion/processing |
| Pandas | Investigation/report processing |
| SQLAlchemy | Database access |
| Psycopg | PostgreSQL driver |
| NetworkX | Graph analysis |
| ReportLab | PDF generation |
| Ollama | Local AI inference |

## Database

```text
PostgreSQL
```

## Infrastructure

```text
Docker
Docker Compose
```

---

# Project Structure

The frontend intentionally uses the existing `src` structure and does not require a `pages` directory.

A representative project structure is:

```text
project-vigilance/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── upload.py
│   │   │   ├── stats.py
│   │   │   ├── detection.py
│   │   │   ├── risk.py
│   │   │   ├── alerts.py
│   │   │   ├── investigation.py
│   │   │   ├── graph.py
│   │   │   ├── ai.py
│   │   │   └── report.py
│   │   ├── ai/
│   │   │   └── explainer.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── init_db.py
│   │   ├── detection/
│   │   │   └── engine.py
│   │   ├── risk/
│   │   │   └── engine.py
│   │   ├── graph/
│   │   │   └── ...
│   │   └── main.py
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── Landing.tsx
│   │   ├── Investigation.tsx
│   │   ├── Investigation.css
│   │   ├── RelationshipGraph.tsx
│   │   └── ...
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── docker-compose.yml
├── README.md
└── ...
```

The exact tree may evolve; the important separation is frontend, FastAPI APIs, detection/risk/graph/AI modules and PostgreSQL.

---

# Data Model

The primary database table is:

```text
transactions
```

Important fields include:

| Column | Purpose |
|---|---|
| id | Internal database row identifier |
| transaction_id | Dataset transaction identifier |
| timestamp | Transaction time |
| sender_account | Sending account |
| sender_name | Sender name where available |
| sender_customer | Sender customer identifier |
| receiver_account | Receiving account |
| receiver_name | Receiver name where available |
| receiver_customer | Receiver customer identifier |
| amount | Transaction amount |
| currency | Currency |
| channel | Payment channel |
| ip_address | Source IP |
| device_id | Device identifier |
| country | Country |
| city | City |
| crypto_flag | Crypto indicator |
| crypto_wallet | Crypto wallet |

The internal `id` is the database row identifier. `transaction_id` is not assumed to be unique because source datasets can contain duplicate transaction identifiers.

---

# Dataset Requirements

## Required columns

```text
transaction_id
timestamp
sender_account
receiver_account
amount
```

## Optional columns

```text
sender_customer
receiver_customer
currency
channel
ip_address
device_id
country
city
crypto_flag
crypto_wallet
```

Example:

```csv
transaction_id,timestamp,sender_account,receiver_account,amount,currency,channel,ip_address,device_id,country,city,crypto_flag,crypto_wallet
TX-001,2026-09-15 10:00:00,ACC-1001,ACC-2001,95000,INR,RTGS,192.168.1.10,DEV-001,IN,Chennai,0,
TX-002,2026-09-15 10:05:00,ACC-1002,ACC-2001,97000,INR,RTGS,192.168.1.10,DEV-001,IN,Chennai,0,
TX-003,2026-09-15 10:10:00,ACC-2001,ACC-3001,180000,INR,IMPS,192.168.1.20,DEV-002,IN,Bengaluru,0,
```

The supplied problem statement specifies CSV/Excel ingestion and requires the dataset to be loaded into a data store in full and accessible through the application's queries/APIs. fileciteturn21file6

---

# Installation

## Prerequisites

Install:

- Git
- Python 3.11+ recommended
- Node.js 20+
- npm
- Docker Desktop
- PostgreSQL client tools (optional, useful for `psql` inspection)
- Ollama for local AI explanation

---

## Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd project-vigilance
```

If the repository is already present locally:

```bash
cd project-vigilance
```

---

# Running the Application

## 1. Start PostgreSQL

The current development database configuration uses:

```text
Host: localhost
Port: 5433
Database: vigilance
Username: vigilance
Password: vigilance
```

Start Docker services:

```bash
docker compose up -d
```

Check:

```bash
docker ps
```

---

## 2. Configure the Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

If ReportLab was added after the initial requirements file:

```powershell
pip install reportlab
```

Initialize database tables:

```powershell
python -m app.db.init_db
```

Start FastAPI:

```powershell
uvicorn app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

Expected:

```json
{
  "status": "ok",
  "service": "project-vigilance"
}
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

---

## 3. Configure the Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Current development URL:

```text
http://localhost:5174
```

---

## 4. Configure Ollama

Install Ollama and verify:

```powershell
ollama --version
```

Pull the current local model:

```powershell
ollama pull qwen2.5:1.5b
```

Verify:

```powershell
ollama list
```

The current application uses:

```text
Model: qwen2.5:1.5b
Endpoint: http://localhost:11434/api/generate
```

---

# First-Time Usage

Start services in this order:

```text
1. Docker / PostgreSQL
2. FastAPI
3. Ollama
4. React/Vite
```

Then open:

```text
http://localhost:5174
```

The intended user journey is:

```text
Landing Page
     ↓
Automated Analysis
     ↓
Upload CSV
     ↓
Dataset Processing
     ↓
Dashboard
     ↓
Alerts
     ↓
Investigation
```

---

# Uploading a Dataset

From the landing page:

1. Select the transaction CSV.
2. Submit it for automated analysis.
3. The backend validates the required columns.
4. Invalid mandatory rows are excluded.
5. The active transaction table is replaced.
6. Valid records are inserted into PostgreSQL.
7. The dashboard becomes available for the new dataset.

The current upload workflow intentionally replaces the active dataset using:

```sql
TRUNCATE TABLE transactions RESTART IDENTITY
```

Therefore:

> **Uploading a new dataset replaces the currently loaded dataset.**

This is appropriate for the current single-dataset hackathon workflow. A production version can introduce dataset IDs and persistent investigation cases.

---

# Investigation Workflow

## 1. Dashboard

Review:

- total transactions
- suspicious alerts
- high-risk entities
- critical entities
- amount statistics
- currency distribution
- channel distribution
- crypto activity
- shared-device/IP indicators

## 2. Alerts

Each alert can contain:

```text
Alert ID
Account / Entity
Risk Score
Risk Level
Detected Patterns
Status
```

## 3. Investigation

Select an alert and open the investigation workspace.

## 4. Risk Evidence

Review:

- risk score
- risk classification
- detected patterns
- reasons

## 5. Transactions

Inspect transactions associated with the entity.

## 6. Timeline

Review the chronological sequence of activity.

## 7. Graph

Explore connected accounts, devices, IP addresses and transaction relationships.

## 8. AI Explanation

Expand the AI explanation only when required. The investigator can continue examining deterministic evidence while the local model is generating.

## 9. Report

Click:

```text
Export Investigation Report
```

The PDF is downloaded locally.

---

# API Reference

Base URL:

```text
http://localhost:8000/api
```

## Upload

```http
POST /api/upload
```

## Statistics

```http
GET /api/stats
```

## Detection

```http
GET /api/detection
```

## Risk

```http
GET /api/risk
```

## Alerts

```http
GET /api/alerts
```

## Investigation

```http
GET /api/investigation/{account}
```

## Relationship Graph

```http
GET /api/graph/{account}
```

## AI Explanation

```http
GET /api/ai/explanation/{account}
```

## Investigation Report

```http
GET /api/report/{account}
```

---

# Large Dataset Considerations

The target AML dataset can contain approximately 250,000 records or more. The database can store that volume, but the browser should not receive and render hundreds of thousands of rows at once.

Recommended architecture:

```text
250,000+ records
      |
      v
 PostgreSQL
      |
      v
Server-side filtering / aggregation
      |
      v
Small API payload
      |
      v
React
```

Avoid:

```text
250,000 records
      |
      v
FastAPI JSON response
      |
      v
React DOM
      |
      v
Browser freeze
```

For transaction tables, use server-side pagination such as:

```http
GET /api/transactions?page=1&page_size=50
```

Dashboard values should preferably be calculated with database aggregations such as:

```sql
COUNT(*)
SUM(amount)
AVG(amount)
MIN(amount)
MAX(amount)
GROUP BY currency
GROUP BY channel
```

This keeps the browser responsive and reduces unnecessary network transfer.

---

# Troubleshooting

## Backend does not start

```powershell
python --version
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## PostgreSQL connection error

```powershell
docker ps
docker compose up -d
```

Confirm port `5433` is available.

## Missing database tables

```powershell
python -m app.db.init_db
```

## Upload fails

Verify the CSV contains:

```text
transaction_id
timestamp
sender_account
receiver_account
amount
```

Check the FastAPI terminal for the exact ingestion error.

## Excel dependency error

The ingestion code uses Polars `read_excel`. For the large AML dataset, CSV is recommended. If XLSX support is needed, install the Excel dependency required by the installed Polars version rather than changing the application's ingestion design.

## Dashboard freezes

Do not send all transaction rows to React. Use aggregation, pagination and server-side filtering.

## AI is slow

Verify:

```powershell
ollama list
```

Test the model:

```powershell
ollama run qwen2.5:1.5b
```

AI generation speed depends on the available CPU/GPU/RAM. The UI is designed so AI explanation can be reviewed separately from the main investigation evidence.

## PDF generation fails

```powershell
pip show reportlab
pip install reportlab
```

Restart FastAPI after dependency changes.

---

# Development Workflow

Recommended development sequence:

```text
Start PostgreSQL
      ↓
Start FastAPI
      ↓
Start Ollama
      ↓
Start React
      ↓
Upload dataset
      ↓
Verify database ingestion
      ↓
Verify statistics
      ↓
Verify detections
      ↓
Verify risk
      ↓
Verify alerts
      ↓
Verify investigation
      ↓
Verify graph
      ↓
Verify timeline
      ↓
Verify AI
      ↓
Verify PDF report
```

The supplied engineering checklist emphasizes meaningful version-control commits, reproducible dependencies, safe configuration, modular code, error handling, logging, testing and documentation. fileciteturn21file6

---

# Testing Checklist

## Data Ingestion

- [ ] CSV upload works
- [ ] XLSX upload works when the required Polars Excel dependency is installed
- [ ] Missing mandatory columns are rejected
- [ ] Invalid mandatory rows are handled
- [ ] Timestamp parsing works
- [ ] Duplicate transaction IDs are reported
- [ ] Full dataset is inserted into PostgreSQL
- [ ] Upload replaces the previous active dataset

## Detection

- [ ] Structuring detection works
- [ ] Layering detection works
- [ ] Circular flow detection works
- [ ] Mule detection works
- [ ] Shared device detection works
- [ ] Shared IP detection works
- [ ] Crypto detection works

## Risk

- [ ] Score remains within 0–100
- [ ] Classification matches score range
- [ ] Pattern contributions are visible
- [ ] Multiple-pattern contribution works

## Dashboard

- [ ] Dataset metrics load
- [ ] Alerts load
- [ ] High-risk count is correct
- [ ] Critical count is correct
- [ ] Large datasets do not freeze the browser

## Investigation

- [ ] Alert opens investigation
- [ ] Transactions load
- [ ] Timeline loads
- [ ] Graph loads
- [ ] Connected entities are visible
- [ ] Graph entities can be selected

## AI

- [ ] Ollama is running
- [ ] Model is installed
- [ ] AI endpoint responds
- [ ] AI explanation is on-demand
- [ ] Markdown-style AI output is rendered cleanly

## Reporting

- [ ] PDF export works
- [ ] Risk score appears
- [ ] AML patterns appear
- [ ] Evidence appears
- [ ] Timeline appears
- [ ] Analyst observation area appears
- [ ] Disclaimer appears
- [ ] PDF opens correctly

---

# Design Decisions

## PostgreSQL + NetworkX

The platform uses PostgreSQL as the transaction source of truth and NetworkX for relationship analysis. This avoids the operational complexity of introducing a separate graph database during the core hackathon workflow.

## FastAPI Modular Backend

The backend is a modular FastAPI application rather than a collection of microservices. This reduces deployment and debugging overhead while keeping detection, risk, graph, AI and reporting responsibilities separated in code.

## Deterministic Risk + AI Explanation

Risk is calculated from explicit detection evidence. AI explains that evidence instead of being the sole source of the risk decision.

## Local AI

Ollama provides local inference. This removes the need for a cloud AI API for the current demonstration and keeps the AI layer local to the development environment.

## Single Active Dataset

The current workflow intentionally supports one active dataset at a time:

```text
Upload
  ↓
Replace
  ↓
Analyze
```

A production system can evolve this into:

```text
Dataset
  ↓
Dataset Version
  ↓
Investigation Case
  ↓
Investigator
```

---

# Limitations

Project Vigilance is an investigation-support prototype.

Important limitations include:

1. Detection rules are heuristic and should not be treated as proof of financial crime.
2. Risk weights are prototype design choices.
3. Shared device/IP relationships may have legitimate explanations.
4. Crypto activity alone does not establish suspicious behaviour.
5. AI-generated explanations can contain errors and require review.
6. The current system is primarily designed for local/hackathon deployment.
7. The upload workflow replaces the active dataset rather than maintaining dataset history.
8. Large transaction tables require server-side pagination/aggregation.
9. Production authentication and role-based access are not part of the current core workflow.
10. Production-grade audit logging, encryption, retention and compliance controls require additional implementation.

The use case also explicitly asks teams to document assumptions, limitations and design decisions and to ensure AI is fair, transparent and ethically designed. fileciteturn21file1

---

# Security and Responsible Use

When using real financial data:

- never commit transaction datasets to Git
- never commit passwords or API keys
- restrict database access
- protect uploaded files
- use encrypted transport in production
- implement authentication
- implement authorization
- maintain audit logs
- apply appropriate data-retention policies
- protect personally identifiable information
- follow applicable financial-data and privacy requirements

The AI layer is decision support. It should not be presented as an autonomous final compliance or legal decision-maker.

---

# Future Enhancements

Potential next-stage capabilities include:

## Investigation Management

- case IDs
- investigation status
- investigator assignment
- case notes
- evidence attachments
- case history

## Advanced Risk Analytics

- Isolation Forest anomaly detection
- customer behavioural baselines
- historical behaviour comparison
- configurable thresholds
- graph-based risk propagation
- relationship confidence scoring

## Advanced Graph Analytics

- community detection
- suspicious-cluster detection
- centrality analysis
- multi-hop money-flow tracing
- money-flow replay

## AI Investigation Copilot

A future optional AI copilot could answer questions such as:

```text
Why was this account flagged?

Show the first suspicious transaction.

Which accounts are connected to this entity?

Which accounts received money shortly after this account?

Summarize this investigation.
```

## Enterprise Features

- authentication
- role-based access
- investigator/compliance/manager roles
- audit logging
- dataset versioning
- case management
- production deployment
- distributed processing
- failure recovery

The supplied use case lists advanced features such as an AI investigation copilot, money-flow replay, role-based access, resilience, relationship confidence scoring, workflow recommendations and configurable thresholds as optional enhancements after the core workflow is complete. fileciteturn21file5

---

# Demo Walkthrough

A strong live demonstration can follow this sequence.

## 1. Landing Page

Explain:

> Project Vigilance converts transaction data into investigation intelligence by combining AML detection, risk scoring, relationship analysis, timelines, explainability and reporting.

## 2. Upload Dataset

Upload the prepared transaction CSV and show that ingestion completes.

## 3. Dashboard

Show transaction volume and suspicious-alert metrics.

## 4. Select a Suspicious Alert

Click:

```text
INVESTIGATE
```

## 5. Risk Assessment

Show:

```text
Risk Score
Risk Level
Detected Patterns
Reasons
```

## 6. Transaction Evidence

Show the transactions associated with the investigated entity.

## 7. Timeline

Explain how chronological events reconstruct the activity story.

## 8. Relationship Graph

Show connected accounts, devices, IP addresses and transaction relationships.

## 9. AI Explanation

Expand the AI section and let the local model produce the explanation.

Explain:

> The AI is an investigator assistant. It explains evidence already calculated by the platform rather than independently determining guilt or final compliance action.

## 10. Investigation Report

Click:

```text
Export Investigation Report
```

Open the generated PDF and demonstrate the structured investigation artifact.

The supplied use case explicitly expects at least one complete suspicious case to be demonstrated from detection through investigation and final reporting. fileciteturn21file5

---

# Project Status

The core Project Vigilance workflow has been implemented around:

```text
Landing Page
      ↓
Dataset Upload
      ↓
Data Processing
      ↓
AML Detection
      ↓
Risk Scoring
      ↓
Alerts
      ↓
Investigation
      ↓
Transaction Evidence
      ↓
Timeline
      ↓
Relationship Graph
      ↓
AI Explanation
      ↓
PDF Investigation Report
```

The project prioritizes a working end-to-end investigation workflow rather than unnecessary infrastructure complexity, consistent with the supplied use case's instruction to prioritize an integrated working solution. fileciteturn21file5

---

# License

This project is developed as a prototype/hackathon solution for AML investigation and decision support.

Refer to the repository for the final licensing terms.

---

# Project Vigilance

**Detect suspicious activity.**  
**Understand the network.**  
**Reconstruct the story.**  
**Support the investigator.**
