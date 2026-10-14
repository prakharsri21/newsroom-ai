import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { AlertCircle, ArrowUpRight, CheckCircle2, ExternalLink, Globe2, LoaderCircle, RefreshCw, Search, ShieldCheck, X } from "lucide-react";
import "./App.css";

type Verdict = "SUPPORTED" | "PARTIALLY_SUPPORTED" | "CONTRADICTED" | "UNVERIFIABLE" | "OUTDATED";
type GenerationStatus = "verified" | "needs_review" | "research_incomplete" | "citation_validation_failed" | "out_of_scope";

type GenerationResult = {
  status: GenerationStatus;
  query: string;
  story_id: number | null;
  article_id: number | null;
  headline: string | null;
  summary: string | null;
  article: string | null;
  research_complete: boolean;
  citation_validation_passed: boolean | null;
  citation_validation_errors: string[];
  fact_check_passed: boolean | null;
  fact_check_reason: string | null;
  research_failure_reason?: string | null;
  sources: {
    evidence_ref: string;
    source_id: number | null;
    title: string;
    publisher: string | null;
    url: string;
    published_at?: string | null;
    authority_tier?: string | null;
  }[];
  claims: {
    claim_index: number;
    claim_text: string;
    verdict: Verdict;
    confidence: number;
    rationale: string;
    supporting_evidence_refs: string[];
    contradicting_evidence_refs: string[];
    reviewed_evidence_refs: string[];
  }[];
  message: string;
};

type TopNewsItem = {
  id: number;
  headline: string;
  summary: string | null;
  category: string;
  published_at: string | null;
  first_seen_at: string;
  source_title: string | null;
  publisher: string | null;
  source_url: string | null;
  verification_status: "not_checked";
  source_count: number;
};

type TopNewsApiResponse = {
  items: TopNewsItem[];
  served_from_cache: boolean;
  refreshed_at: string | null;
  message: string;
  detail?: string;
};

type Story = {
  id: string;
  category: string;
  title: string;
  summary: string;
  published: string;
  publisher: string;
  sourceUrl: string | null;
  verificationStatus: "not_checked";
  sourceCount: number;
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
const CATEGORY_FILTERS = ["All", "National", "World", "Markets", "Technology", "Sports", "Entertainment"] as const;
type CategoryFilter = (typeof CATEGORY_FILTERS)[number];

const STATUS_LABELS: Record<GenerationStatus, string> = {
  verified: "Verified",
  needs_review: "Needs review",
  research_incomplete: "Research incomplete",
  citation_validation_failed: "Citation validation failed",
  out_of_scope: "Out of scope",
};

const VERDICT_LABELS: Record<Verdict, string> = {
  SUPPORTED: "Supported",
  PARTIALLY_SUPPORTED: "Partially supported",
  CONTRADICTED: "Contradicted",
  UNVERIFIABLE: "Unverifiable",
  OUTDATED: "Outdated",
};

function formatDate(value: string | null | undefined): string {
  if (!value) return "Publication time unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Publication time unavailable";
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(date) + " UTC";
}

function mapTopNewsItem(item: TopNewsItem): Story {
  let publisher = item.publisher || "";
  if (!publisher && item.source_url) {
    try {
      publisher = new URL(item.source_url).hostname.replace(/^www\./, "");
    } catch {
      publisher = "Source details unavailable";
    }
  }

  return {
    id: String(item.id),
    category: item.category || "World",
    title: item.headline,
    summary: item.summary?.trim() || "The publisher did not provide a short summary for this report.",
    published: item.published_at ? formatDate(item.published_at) : `Discovered ${formatDate(item.first_seen_at)}`,
    publisher: publisher || "Source details unavailable",
    sourceUrl: item.source_url,
    verificationStatus: item.verification_status,
    sourceCount: item.source_count,
  };
}

function normalizeText(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

function getArticleBullets(result: GenerationResult): string[] {
  const paragraphs = (result.article || "")
    .split(/\n\s*\n/)
    .map((paragraph) => paragraph.trim().replace(/^[-*•\d.)\s]+(?=\S)/, ""))
    .filter(Boolean);

  const normalizeEditorialText = (value: string) =>
    normalizeText(value)
      // The editor formats grouped refs as [E1, E2], not [E1], [E2].
      .replace(/(?:\s*\[e\d+(?:\s*,\s*e\d+)*\])+\s*$/i, "")
      .trim();
  const headline = normalizeEditorialText(result.headline || "");
  const summary = normalizeEditorialText(result.summary || "");

  const filtered = paragraphs.filter((paragraph) => {
    const normalized = normalizeEditorialText(paragraph);
    return normalized !== headline && normalized !== summary;
  });

  return filtered;
}

function App() {
  const [stories, setStories] = useState<Story[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [newsError, setNewsError] = useState("");
  const [newsMessage, setNewsMessage] = useState("");
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("All");
  const [query, setQuery] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generated, setGenerated] = useState<GenerationResult | null>(null);
  const [searchError, setSearchError] = useState("");
  const searchInput = useRef<HTMLInputElement>(null);
  const initialLoadDone = useRef(false);

  const loadTopNews = useCallback(async (forceRefresh = false) => {
    setNewsLoading(true);
    setNewsError("");
    try {
      const url = new URL(`${API_BASE_URL}/news/top`);
      url.searchParams.set("limit", "10");
      if (forceRefresh) url.searchParams.set("refresh", "true");

      const response = await fetch(url.toString(), { cache: "no-store" });
      const payload = (await response.json()) as TopNewsApiResponse;
      if (!response.ok) {
        throw new Error(payload.detail || `News request failed (${response.status}).`);
      }

      const items = (payload.items || []).map(mapTopNewsItem);
      setStories(items);
      setNewsMessage(payload.message || "News feed loaded.");
      setRefreshedAt(payload.refreshed_at);
      if (items.length === 0) {
        setNewsError("No suitable recent headlines were returned. Try refreshing in a moment.");
      }
    } catch (error) {
      setNewsError(error instanceof Error ? error.message : "Could not connect to the newsroom API.");
    } finally {
      setNewsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;
    // Prefer the backend's 30-minute cache on page load; manual refresh bypasses it.
    void loadTopNews(false);
  }, [loadTopNews]);

  const visibleStories = useMemo(() => {
    if (categoryFilter === "All") return stories;
    return stories.filter((story) => story.category.toLowerCase() === categoryFilter.toLowerCase());
  }, [stories, categoryFilter]);

  async function runGeneration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 3) {
      setSearchError("Enter a topic with at least 3 characters.");
      searchInput.current?.focus();
      return;
    }

    setQuery(trimmed);
    setIsGenerating(true);
    setSearchError("");
    setGenerated(null);

    try {
      const response = await fetch(`${API_BASE_URL}/news/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed, category: categoryFilter === "All" ? "General" : categoryFilter }),
      });
      const payload = (await response.json()) as GenerationResult & { detail?: string };
      if (!response.ok) throw new Error(payload.detail || `News generation failed (${response.status}).`);
      setGenerated(payload);
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : "Could not reach the newsroom API.");
    } finally {
      setIsGenerating(false);
    }
  }

  const generatedBullets = generated ? getArticleBullets(generated) : [];

  return (
    <div className="app-frame">
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Newsroom AI home">
          <span className="brand-mark"><Globe2 size={21} strokeWidth={1.7} /></span>
          <span><strong>Newsroom <em>AI</em></strong><small>RESEARCHED. WRITTEN. CHECKED.</small></span>
        </a>
        <button className="refresh-button" onClick={() => void loadTopNews(true)} disabled={newsLoading}>
          {newsLoading ? <LoaderCircle className="spin" size={16} /> : <RefreshCw size={15} />}
          {newsLoading ? "Loading news" : "Refresh news"}
        </button>
      </header>

      <main id="top" className="page-content">
        <section className="intro-block">
          <p className="eyebrow"><span className="live-dot" /> CURRENT AFFAIRS, WITH CONTEXT</p>
          <h1>The news, <span>made clearer.</span></h1>
          <p className="intro-copy">Browse current headlines or search a topic to generate a sourced report with claim-level fact checks.</p>
        </section>

        <form className="search-form" onSubmit={runGeneration}>
          <Search size={19} className="search-icon" />
          <input
            ref={searchInput}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search a topic, event, person or question…"
            aria-label="Search news topic"
            disabled={isGenerating}
          />
          {query && !isGenerating && <button className="clear-search" type="button" aria-label="Clear search" onClick={() => { setQuery(""); setSearchError(""); searchInput.current?.focus(); }}><X size={15} /></button>}
          <button className="search-button" type="submit" disabled={isGenerating}>
            {isGenerating ? <LoaderCircle className="spin" size={16} /> : <Search size={16} />}
            {isGenerating ? "Researching" : "Research topic"}
          </button>
        </form>

        {searchError && <div className="message error-message" role="alert"><AlertCircle size={17} /><span>{searchError}</span></div>}

        {isGenerating && (
          <div className="generation-progress" role="status">
            <LoaderCircle className="spin" size={19} />
            <div><strong>Researching your topic</strong><span>The newsroom is gathering sources, drafting a report and checking its claims. This can take a little while.</span></div>
          </div>
        )}

        {generated && (
          <section className="generated-panel" aria-live="polite">
            <div className="generated-topline">
              <p className="eyebrow">{generated.status === "out_of_scope" ? "NEWSROOM AI SCOPE" : "YOUR NEWSROOM REPORT"}</p>
              <span className={`status-badge status-${generated.status}`}>{STATUS_LABELS[generated.status] || generated.status}</span>
            </div>
            <h2>{generated.status === "out_of_scope" ? "Newsroom AI is for news research" : generated.headline || generated.query}</h2>
            {generated.status === "out_of_scope" ? (
              <p className="generated-summary">{generated.message}</p>
            ) : (
              <>

            {generated.summary && <p className="generated-summary">{generated.summary}</p>}
            {generated.research_failure_reason && <p className="inline-warning">Research note: {generated.research_failure_reason}</p>}
            {generated.citation_validation_errors?.length > 0 && (
              <div className="inline-warning">Citation validation: {generated.citation_validation_errors.join("; ")}</div>
            )}
            {generatedBullets.length > 0 && <ul className="article-bullets">{generatedBullets.map((bullet, index) => <li key={`${index}-${bullet.slice(0, 30)}`}>{bullet}</li>)}</ul>}

            <div className="generated-checks">
              <span><ShieldCheck size={15} /> Fact check: <strong>{generated.fact_check_passed === true ? "Passed" : generated.fact_check_passed === false ? "Needs review" : "Not confirmed"}</strong></span>
              <span><CheckCircle2 size={15} /> Citation validation: <strong>{generated.citation_validation_passed === true ? "Passed" : generated.citation_validation_passed === false ? "Failed" : "Not confirmed"}</strong></span>
            </div>

            {generated.claims.length > 0 && (
              <details className="claims-details">
                <summary>View claim checks ({generated.claims.length})</summary>
                <div className="claim-list">
                  {generated.claims.map((claim) => <article className="claim-item" key={claim.claim_index}>
                    <div className="claim-heading"><span>CLAIM {String(claim.claim_index + 1).padStart(2, "0")}</span><strong className={`verdict verdict-${claim.verdict.toLowerCase()}`}>{VERDICT_LABELS[claim.verdict]}</strong></div>
                    <p>{claim.claim_text}</p>
                    <small>{claim.rationale}</small>
                    <small className="claim-evidence">Evidence reviewed: {claim.reviewed_evidence_refs.join(", ") || "None listed"}</small>
                  </article>)}
                </div>
              </details>
            )}

            <div className="sources-section">
              <h3>Sources used</h3>
              {generated.sources.length > 0 ? <ol className="source-list">{generated.sources.map((source) => <li key={source.evidence_ref}>
                <span className="source-reference">{source.evidence_ref}</span>
                <div className="source-text"><a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url} <ExternalLink size={12} /></a><span>{source.publisher || source.authority_tier || "Publisher unavailable"}{source.published_at ? ` · ${formatDate(source.published_at)}` : ""}</span></div>
              </li>)}</ol> : <p className="empty-note">The API did not return source links for this report.</p>}
            </div>
            
                <p className="report-note">{generated.message}</p>
              </>
            )}
          </section>
        )}

        <section className="news-section">
          <div className="section-heading">
            <div><p className="eyebrow">THE LATEST</p><h2>Latest news</h2></div>
            <span className="story-count">{visibleStories.length} {visibleStories.length === 1 ? "story" : "stories"}</span>
          </div>

          <div className="category-filters" aria-label="Filter by category">
            {CATEGORY_FILTERS.map((filter) => <button key={filter} className={categoryFilter === filter ? "filter-chip active" : "filter-chip"} onClick={() => setCategoryFilter(filter)} type="button">{filter}</button>)}
          </div>

          {newsLoading && stories.length === 0 && <div className="feed-state"><LoaderCircle className="spin" size={20} /><span>Finding current headlines…</span></div>}
          {!newsLoading && visibleStories.length === 0 && !newsError && <div className="feed-state"><Globe2 size={20} /><span>No stories in this category yet. Choose another category or refresh the news.</span></div>}
          {newsError && stories.length === 0 && <div className="message error-message"><AlertCircle size={17} /><span>{newsError}</span><button onClick={() => void loadTopNews(true)}>Try again</button></div>}

          {visibleStories.length > 0 && <div className="news-list">
            {visibleStories.map((story) => <article className="news-item" key={story.id}>
              <div className="news-item-main">
                <div className="news-meta"><span className="category-label">{story.category}</span><span className="meta-separator">·</span><span>{story.published}</span></div>
                <h3>{story.sourceUrl ? <a href={story.sourceUrl} target="_blank" rel="noreferrer">{story.title}<ArrowUpRight size={16} /></a> : story.title}</h3>
                <p>{story.summary}</p>
                <div className="news-footer"><span className="publisher"><Globe2 size={13} />{story.publisher}</span><span className="verification-note">Not fact-checked by Newsroom AI</span></div>
              </div>
            </article>)}
          </div>}
          {newsError && stories.length > 0 && <div className="message soft-error"><AlertCircle size={15} /><span>{newsError}</span></div>}
          {newsMessage && stories.length > 0 && <p className="feed-note">{newsMessage}{refreshedAt ? ` · Last refreshed ${formatDate(refreshedAt)}` : ""}</p>}
        </section>

        <footer className="site-footer"><span>NEWSROOM AI</span><span>Discovery headlines are not verified until you run a newsroom report.</span></footer>
      </main>
    </div>
  );
}

export default App;
