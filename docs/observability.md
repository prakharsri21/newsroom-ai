# Newsroom AI observability runbook

## What is traced

The `POST /news/generate` flow is represented by a `generate-news` parent span. Its child observations include the query planner, newsroom graph, researcher iterations, news-search tool calls, Tavily web-search requests, editor, and fact checker. Langfuse records observation durations automatically; the application adds metadata to explain what each stage did.

The tracing instrumentation is diagnostic. It must not decide whether an article is accurate; use the returned citations and claim-verification results for that.

## Generation-level metadata

The `generate-news` span records:

- `query_plan_ms`, `graph_ms`, `evidence_persistence_ms`, `article_persistence_ms`, `response_build_ms`, and `total_pipeline_ms` (milliseconds).
- `query_plan_intent`, `query_plan_fallback`, `planned_follow_up_count`, and `planned_search_days`.
- `research_complete`, `last_research_loop_iteration`, `research_query_count`, `evidence_count`, `source_count`, and `claim_count`.
- `status`, `citation_validation_passed`, and `fact_check_passed`. These indicate pipeline outputs, not a guarantee that every claim is true.

On failure, the root span records `pipeline_status=error`, `failure_stage`, `error_type`, any timings completed so far, and total elapsed time.

## Observation-level metadata

- **query-planner**: current/historical intent, follow-up count, date-window choice, whether the deterministic fallback ran, and primary-query length.
- **researcher-node**: iteration, intent, whether it is a fact-check follow-up, forced planned-search behavior, requested tool-call count, collected query/evidence counts, and completion state.
- **search-news-tool**: effective date window, historical mode, number of search attempts, whether the empty-result fallback ran, fallback window, and result count.
- **web-search**: provider, Tavily result count, requested result limit, query length, search depth, and date window. Observation duration identifies slow provider calls.
- **fetch-source / fetch-source-http**: direct HTTP extraction status, method, and text length; when Firecrawl fallback is needed, `fallback_status` moves from `started` to `success` or `error`, with the triggering error type and fallback extraction method/text length or fallback error type. The HTTP child may be marked errored even when the parent succeeds through Firecrawl; inspect the parent outcome to distinguish recovered failures from total fetch failures.
- **editor-node**: elapsed time, evidence/claim/paragraph counts, draft length, and citation-validation outcome.
- **fact-checker-node**: elapsed time, attempt number, claim count, supported vs. non-supported claim count, verdict outcome, and whether extra research was requested.

Agent-state inputs and outputs are not captured on the generation parent, newsroom graph, researcher, editor, or fact-checker wrapper spans. The web-search observation still captures its search query input to make retrieval behavior diagnosable; do not send secrets or private data as news-search terms.

## How to establish a baseline

1. In Langfuse, filter observations by `generate-news` and inspect complete traces rather than comparing only the overall duration.
2. Run a small repeatable set of topics: a current headline, a historically scoped query, an ambiguous acronym, a query with little available evidence, and a query that needs a fact-check follow-up. Repeat each several times.
3. Compare `total_pipeline_ms` and stage timings, then open the slowest trace. If `graph_ms` is high, compare the individual `researcher-node`, `web-search`, `editor-node`, and `fact-checker-node` durations. Multiple `web-search` observations usually indicate planned follow-ups or an empty-result date-window retry.
4. Examine quality and cost proxies alongside latency: result counts, search attempts, fallback rates, evidence and source counts, research completion, citation validation, and fact-check outcome.
5. Optimize the stage that is consistently slow across representative traces. Do not reduce follow-up searches or verification steps solely to improve elapsed time; compare quality outcomes before and after a change.

Record the model/configuration, date range, number of traces, and query mix when sharing baseline measurements. This helps avoid drawing conclusions from a single unusual request.
