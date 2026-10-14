# Newsroom AI

Newsroom AI is an agentic news-research and writing application. It discovers reporting for a topic, gathers source evidence, drafts an article with citations, validates those citations, and checks individual claims before presenting the result.

> **Editorial note:** A `verified` status means the application's research, citation, and fact-check checks passed. It is not a guarantee of truth. Review the cited sources before publishing.

## What it does

- **News feed:** Browse recent headlines by category. The initial feed uses a 30-minute backend cache; the refresh action requests fresh discovery.
- **Query planning:** Turns a user topic into a focused search plan and supports current or explicitly historical research.
- **Agentic research:** A LangGraph workflow coordinates the Researcher, Editor, and Fact Checker.
- **Evidence and citations:** Stores source records and evidence relationships; checks article citations against the collected evidence.
- **Claim verification:** Returns per-claim verdicts, rationales, and supporting or contradicting evidence references.
- **Source extraction fallback:** Tries direct HTTP/BeautifulSoup extraction and falls back to Firecrawl when direct extraction fails or yields too little text.
- **Observability:** Langfuse traces the generation pipeline and records stage timings and low-cardinality diagnostic metadata.

## Stack

**Backend:** Python 3.12+, FastAPI, LangGraph, LangChain/OpenAI, SQLAlchemy async, Alembic, PostgreSQL, Tavily, Firecrawl, Langfuse  
**Frontend:** React, TypeScript, Vite  
**Local database:** PostgreSQL 17 via Docker Compose

## Architecture

```text
React + Vite
    |
    v
FastAPI
    |
    +--> Cached top-news feed
    |
    +--> Query planner
             |
             v
         LangGraph
       Researcher -> Editor -> Fact Checker
             |          |
             v          v
        Tavily search  Citation validation
             |
             v
       HTTP/BeautifulSoup -> Firecrawl fallback
             |
             v
        PostgreSQL: sources, stories, articles,
        claims, fact checks, and relationships

Langfuse traces generation stages and fetch/research outcomes.
```

## Local setup

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm (Node 22+ recommended)
- Docker Desktop or Docker Engine
- API credentials for OpenAI, Tavily, Firecrawl, and Langfuse

### 1. Configure environment variables

At the repository root:

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder credentials. Keep `.env` private; it is git-ignored. The included Docker Compose PostgreSQL credentials are for local development only.

### 2. Start PostgreSQL and install Python dependencies

From the repository root:

```bash
docker compose up -d postgres
uv sync --dev
```

### 3. Apply migrations and start the API

In a terminal:

```bash
cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Check the health endpoint at [http://localhost:8000/health](http://localhost:8000/health). Interactive API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

### 4. Start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The frontend defaults to `http://localhost:8000` for the API. To override it, create `frontend/.env.local` with:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

## API quick reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Service health |
| `GET` | `/news/top?limit=10` | Get the cached/discovered news feed |
| `GET` | `/news/top?limit=10&refresh=true` | Force fresh top-news discovery |
| `POST` | `/news/generate` | Research, draft, cite, and fact-check a requested topic |
| `POST` | `/news/stories` | Create a basic story record |
| `GET` | `/news/stories/{story_id}` | Retrieve a story record |

Example generation request:

```bash
curl -X POST http://localhost:8000/news/generate \
  -H 'Content-Type: application/json' \
  -d '{"query":"Latest official updates on a current sports topic","category":"Sports"}'
```

Inspect the returned `status`, `citation_validation_passed`, `fact_check_passed`, `sources`, and `claims`. Results that need review or have incomplete research should not be treated as verified reporting.

## Validation

Start PostgreSQL, configure `.env`, and apply migrations before running the backend tests.

Backend tests:

```bash
cd backend
uv run pytest -q
```

Targeted lint for the recently updated research and fetch paths:

```bash
uv run ruff check app/graph/researcher_agent.py app/services/web_fetch.py tests/test_researcher_agent.py tests/test_web_fetch.py
```

Frontend production build:

```bash
cd frontend
npm ci
npm run build
```

Langfuse tracing fields and guidance are documented in [docs/observability.md](docs/observability.md).

## Project boundaries

- News retrieval and model output depend on external providers, their availability, and API limits.
- A passed check is a useful quality signal, not a replacement for editorial review.
- The Docker Compose database configuration is intended for local development, not production deployment.
