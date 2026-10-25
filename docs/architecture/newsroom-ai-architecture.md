# Newsroom AI — Architecture

> Source-grounded documentation based on the repository's `main` branch. This diagram reflects code paths found in the implementation; planned components are not assumed.

## 1. System map

```mermaid
flowchart TD
  U[User] --> FE[React + TypeScript / Vite]
  FE --> API[FastAPI news router]
  API --> TOP[GET /news/top]
  TOP --> TOPSVC[get_top_news service]
  TOPSVC --> TAVILY[Tavily news search]
  TOPSVC --> CACHE[(PostgreSQL discovery rows / 30-min cache)]
  API --> GEN[POST /news/generate]
  GEN --> SVC[generate_news service]
  SVC --> PLAN[Query Planner + scope gate]
  PLAN -->|Out of scope| REJECT[Return rejection; no graph/search/persistence]
  PLAN -->|In scope| GRAPH[Outer LangGraph]
  GRAPH --> RESEARCH[Researcher subgraph]
  RESEARCH <--> TOOL[search_news tool]
  TOOL --> TAVILY
  GRAPH --> EDITOR[Editor agent]
  EDITOR --> CITATION[Citation reference validation]
  CITATION -->|Pass| FC[Fact Checker agent]
  CITATION -->|Fail| REVIEW[Stop; needs review]
  FC -->|Unsupported / unresolved| LOOP[Bounded feedback routing]
  LOOP -->|Revise draft| EDITOR
  LOOP -->|Need more evidence| RESEARCH
  GRAPH --> OUT[Graph result + collected evidence]
  OUT --> INGEST[Evidence persistence and source ingestion]
  INGEST --> FETCH[HTTPX + BeautifulSoup; Firecrawl fallback]
  FETCH --> DB[(PostgreSQL: sources, stories, articles, claims, checks, links)]
  DB --> RESP[Build API response]
  RESP --> FE
  SVC -. spans / timings .-> LF[Langfuse observability]
  GRAPH -. spans / outcomes .-> LF
  INGEST -. extraction metadata .-> LF
```

### Important separation

- The top-news feed is a separate path from article generation. Discovery stories use the `news_stories` table and a `last_refreshed_at` timestamp; a fresh cache is reused for 30 minutes.
- The Query Planner checks scope before the graph runs. Out-of-scope requests stop before searching, article generation, evidence persistence, or database writes.
- The Researcher and the Editor/Fact Checker operate on the evidence held in graph state. After the graph returns, the service fetches and normalizes source pages while persisting evidence, then stores the article and claim-verification results.
- A `verified` result means the implemented citation and claim checks passed. It is not a guarantee that every claim is true; review the source links before publication.

## 2. Outer LangGraph workflow

```mermaid
flowchart TD
  START([Start]) --> R[Research subgraph]
  R -->|research_complete = true| E[Editor node]
  R -->|incomplete / no usable evidence| END1([End: incomplete result])
  E -->|citation validation passed| F[Fact Checker node]
  E -->|citation validation failed| END2([End: needs review])
  F -->|fact_check_passed = true| END3([End: verified checks])
  F -->|attempts >= 3| END4([End: needs review])
  F -->|next_action = editor| E
  F -->|next_action = researcher| PREP[Prepare follow-up research]
  PREP --> R
```

## 3. Inner Researcher graph

```mermaid
flowchart LR
  START([Start]) --> AGENT[Researcher agent]
  AGENT --> DECIDE{Tool call requested and below iteration limit?}
  DECIDE -->|Yes| TOOL[ToolNode: search_news]
  TOOL --> AGENT
  DECIDE -->|No| END([Return research result])
```

The Researcher loop is capped at four iterations. `search_news` calls Tavily, with up to three results per call; current-news searches can widen the date window once when a narrower search yields no results. Follow-up research preserves already collected evidence while resetting the prior tool-call messages.

## 4. Data model

```mermaid
erDiagram
  NEWS_STORIES ||--o{ ARTICLES : has
  ARTICLES ||--o{ CLAIMS : contains
  CLAIMS ||--o{ FACT_CHECKS : reviewed_by
  NEWS_STORIES ||--o{ STORY_SOURCES : cites_or_discovers
  SOURCES ||--o{ STORY_SOURCES : linked_to
  CLAIMS ||--o{ CLAIM_SOURCES : evaluated_against
  SOURCES ||--o{ CLAIM_SOURCES : evidence_for
```

| Entity | Role |
|---|---|
| `news_stories` | Story headline, summary, category, publication metadata, discovery flag and cache refresh timestamp. |
| `articles` | Generated article content and version; foreign key to `news_stories`. |
| `sources` | Canonical URL, publisher/domain, dates and extracted content; URL is unique. |
| `claims` | Discrete factual claims extracted from an article, with status and confidence. |
| `fact_checks` | Verdict, confidence and rationale for a reviewed claim. |
| `story_sources` | Link table connecting stories and sources. |
| `claim_sources` | Link table connecting claims and reviewed evidence, including support/contradiction relationship and excerpt. |

Langfuse tracing is external observability, not a table in the application schema. PostgreSQL access uses async SQLAlchemy sessions, and Alembic manages schema migrations.

## 5. Useful source files

- [Frontend request and display flow](../../frontend/src/App.tsx)
- [FastAPI routes](../../backend/app/api/news.py)
- [Generation orchestration and persistence](../../backend/app/services/generation.py)
- [Query Planner and scope gate](../../backend/app/graph/query_planner.py)
- [Outer workflow routing](../../backend/app/graph/graph.py)
- [Inner Researcher graph](../../backend/app/graph/research_graph.py)
- [Researcher agent](../../backend/app/graph/researcher_agent.py)
- [Editor agent](../../backend/app/graph/editor_agent.py)
- [Fact Checker agent](../../backend/app/graph/fact_checker_agent.py)
- [Search tool](../../backend/app/graph/tools/research_tools.py)
- [Source page extraction and Firecrawl fallback](../../backend/app/services/web_fetch.py)
- [Source ingestion](../../backend/app/services/source_ingestion.py)
- [Top-news discovery and cache](../../backend/app/services/top_news.py)
- [SQLAlchemy models](../../backend/app/models/)

## Notes

This document is architectural documentation only. It does not change runtime code, prompts, database schema or API behavior.