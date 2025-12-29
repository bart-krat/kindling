"use client";

import { useState } from "react";

interface SearchResults {
  name: string;
  linkedin: {
    profile_url: string;
    all_urls: string[];
  } | null;
  twitter: {
    profile_url: string;
    all_urls: string[];
    username?: string;
    user_id?: string;
  } | null;
  instagram: {
    profile_url: string;
    all_urls: string[];
  } | null;
  image: {
    filename: string;
    url: string;
    title?: string;
    source?: string;
  } | null;
  articles: string[] | null;
}

interface ScrapeResults {
  success: boolean;
  message: string;
  twitter_file?: string;
  linkedin_file?: string;
  twitter_count?: number;
  linkedin_count?: number;
}

interface PerspectiveResults {
  perspective: string;
  sources: Array<{
    rank: number;
    category: string;
    summary: string;
    relevance_score?: number;
  }>;
  query: string;
}

export default function Home() {
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scraping, setScraping] = useState(false);
  const [scrapeResults, setScrapeResults] = useState<ScrapeResults | null>(null);
  const [scrapeError, setScrapeError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [perspectiveLoading, setPerspectiveLoading] = useState(false);
  const [perspectiveResults, setPerspectiveResults] = useState<PerspectiveResults | null>(null);
  const [perspectiveError, setPerspectiveError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError("Please enter a name to search");
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch("http://localhost:8000/api/search-profiles", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: searchQuery.trim(),
          top_n: 2,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to search profiles");
      }

      const data: SearchResults = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred while searching");
      console.error("Search error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleKeyPressQuestion = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleAskQuestion();
    }
  };

  const handleAskQuestion = async () => {
    if (!question.trim()) {
      setPerspectiveError("Please enter a question");
      return;
    }

    setPerspectiveLoading(true);
    setPerspectiveError(null);
    setPerspectiveResults(null);

    try {
      const response = await fetch("http://localhost:8000/api/generate-perspective", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: question.trim(),
          top_k: 5,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate perspective");
      }

      const data: PerspectiveResults = await response.json();
      setPerspectiveResults(data);
    } catch (err) {
      setPerspectiveError(err instanceof Error ? err.message : "An error occurred while generating perspective");
      console.error("Perspective error:", err);
    } finally {
      setPerspectiveLoading(false);
    }
  };

  const handleScrape = async () => {
    if (!results) {
      setScrapeError("No search results available. Please search first.");
      return;
    }

    // Check if we have at least one profile to scrape
    if (!results.twitter?.user_id && !results.linkedin?.profile_url) {
      setScrapeError("No profiles available to scrape. Both Twitter and LinkedIn are missing.");
      return;
    }

    setScraping(true);
    setScrapeError(null);
    setScrapeResults(null);

    try {
      const response = await fetch("http://localhost:8000/api/scrape-profiles", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: results.twitter?.user_id || null,
          linkedin_url: results.linkedin?.profile_url || null,
          name: results.name,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to scrape profiles");
      }

      const data: ScrapeResults = await response.json();
      setScrapeResults(data);
    } catch (err) {
      setScrapeError(err instanceof Error ? err.message : "An error occurred while scraping");
      console.error("Scrape error:", err);
    } finally {
      setScraping(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center font-sans" style={{ backgroundColor: "var(--background)" }}>
      <main className="flex min-h-screen w-full max-w-3xl flex-col items-center justify-center py-32 px-16 sm:items-start">
        <div className="w-full mb-8">
          <div className="flex gap-3 items-center">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter a name to search (e.g., Elon Musk)..."
              className="flex-1 px-4 py-3 rounded-lg border-2 text-lg focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors disabled:opacity-50"
              style={{
                backgroundColor: "var(--pastel-yellow)",
                borderColor: "var(--pastel-brown)",
                color: "var(--foreground)",
              }}
              disabled={loading}
            />
            <button
              onClick={handleSearch}
              disabled={loading}
              className="px-6 py-3 rounded-lg font-medium text-lg transition-colors hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: "var(--pastel-pink)",
                color: "var(--foreground)",
              }}
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
        </div>

        {error && (
          <div className="w-full mb-4 p-4 rounded-lg" style={{ backgroundColor: "var(--pastel-pink)" }}>
            <p className="text-red-700 font-medium">Error: {error}</p>
          </div>
        )}

        {results && (
          <div className="w-full space-y-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-semibold" style={{ color: "var(--foreground)" }}>
                Results for: {results.name}
              </h2>
              {(results.twitter?.user_id || results.linkedin?.profile_url) && (
                <button
                  onClick={handleScrape}
                  disabled={scraping}
                  className="px-6 py-3 rounded-lg font-medium text-lg transition-colors hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: "var(--accent-brown)",
                    color: "var(--background)",
                  }}
                >
                  {scraping ? "Scraping..." : "Scrape Posts"}
                </button>
              )}
            </div>

            {results.linkedin && (
              <div className="p-4 rounded-lg border-2" style={{ backgroundColor: "var(--pastel-brown)", borderColor: "var(--pastel-brown)" }}>
                <h3 className="text-xl font-medium mb-2" style={{ color: "var(--foreground)" }}>LinkedIn</h3>
                <a
                  href={results.linkedin.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline break-all"
                >
                  {results.linkedin.profile_url}
                </a>
              </div>
            )}

            {results.twitter && (
              <div className="p-4 rounded-lg border-2" style={{ backgroundColor: "var(--pastel-brown)", borderColor: "var(--pastel-brown)" }}>
                <h3 className="text-xl font-medium mb-2" style={{ color: "var(--foreground)" }}>X (Twitter)</h3>
                <a
                  href={results.twitter.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline break-all block mb-2"
                >
                  {results.twitter.profile_url}
                </a>
                {results.twitter.username && (
                  <p className="text-sm" style={{ color: "var(--foreground)" }}>
                    Username: @{results.twitter.username}
                  </p>
                )}
                {results.twitter.user_id && (
                  <p className="text-sm" style={{ color: "var(--foreground)" }}>
                    User ID: {results.twitter.user_id}
                  </p>
                )}
              </div>
            )}

            {results.instagram && (
              <div className="p-4 rounded-lg border-2" style={{ backgroundColor: "var(--pastel-brown)", borderColor: "var(--pastel-brown)" }}>
                <h3 className="text-xl font-medium mb-2" style={{ color: "var(--foreground)" }}>Instagram</h3>
                <a
                  href={results.instagram.profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline break-all"
                >
                  {results.instagram.profile_url}
                </a>
              </div>
            )}

            {results.image && (
              <div className="p-4 rounded-lg border-2" style={{ backgroundColor: "var(--pastel-brown)", borderColor: "var(--pastel-brown)" }}>
                <h3 className="text-xl font-medium mb-2" style={{ color: "var(--foreground)" }}>Profile Image</h3>
                <div className="flex flex-col items-start gap-2">
                  <img
                    src={`/${results.image.filename}`}
                    alt={results.image.title || "Profile image"}
                    className="max-w-full h-auto rounded-lg border-2"
                    style={{ 
                      maxHeight: "400px",
                      borderColor: "var(--pastel-pink)"
                    }}
                  />
                  {results.image.title && (
                    <p className="text-sm" style={{ color: "var(--foreground)" }}>
                      {results.image.title}
                    </p>
                  )}
                  {results.image.source && (
                    <p className="text-sm" style={{ color: "var(--foreground)" }}>
                      Source: {results.image.source}
                    </p>
                  )}
                </div>
              </div>
            )}

            {results.articles && results.articles.length > 0 && (
              <div className="p-4 rounded-lg border-2" style={{ backgroundColor: "var(--pastel-brown)", borderColor: "var(--pastel-brown)" }}>
                <h3 className="text-xl font-medium mb-3" style={{ color: "var(--foreground)" }}>Articles</h3>
                <ul className="space-y-2">
                  {results.articles.map((articleUrl, index) => (
                    <li key={index}>
                      <a
                        href={articleUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline break-all block"
                      >
                        {articleUrl}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!results.linkedin && !results.twitter && !results.instagram && !results.image && (!results.articles || results.articles.length === 0) && (
              <div className="p-4 rounded-lg" style={{ backgroundColor: "var(--pastel-yellow)" }}>
                <p style={{ color: "var(--foreground)" }}>No profiles found for this name.</p>
              </div>
            )}

            {/* Scrape Error */}
            {scrapeError && (
              <div className="w-full mb-4 p-4 rounded-lg" style={{ backgroundColor: "var(--pastel-pink)" }}>
                <p className="text-red-700 font-medium">Scrape Error: {scrapeError}</p>
              </div>
            )}

            {/* Scrape Results */}
            {scrapeResults && (
              <div className="w-full space-y-3 p-4 rounded-lg border-2" style={{ backgroundColor: "var(--pastel-yellow)", borderColor: "var(--accent-yellow)" }}>
                <h3 className="text-xl font-semibold" style={{ color: "var(--foreground)" }}>
                  {scrapeResults.success ? "✓ Scraping Completed!" : "⚠ Scraping Partially Completed"}
                </h3>
                <p className="text-sm" style={{ color: "var(--foreground)" }}>
                  {scrapeResults.message}
                </p>
                
                {scrapeResults.twitter_count !== undefined && scrapeResults.twitter_count > 0 && (
                  <div className="mt-2">
                    <p className="font-medium" style={{ color: "var(--foreground)" }}>
                      Twitter: {scrapeResults.twitter_count} posts scraped
                    </p>
                    {scrapeResults.twitter_file && (
                      <p className="text-xs text-gray-600 break-all">
                        Saved to: {scrapeResults.twitter_file}
                      </p>
                    )}
                  </div>
                )}
                
                {scrapeResults.linkedin_count !== undefined && scrapeResults.linkedin_count > 0 && (
                  <div className="mt-2">
                    <p className="font-medium" style={{ color: "var(--foreground)" }}>
                      LinkedIn: {scrapeResults.linkedin_count} posts scraped
                    </p>
                    {scrapeResults.linkedin_file && (
                      <p className="text-xs text-gray-600 break-all">
                        Saved to: {scrapeResults.linkedin_file}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Question/Perspective Section */}
        <div className="w-full mt-8 pt-8 border-t-2" style={{ borderColor: "var(--pastel-brown)" }}>
          <h2 className="text-2xl font-semibold mb-4" style={{ color: "var(--foreground)" }}>
            Ask a Question
          </h2>
          <p className="text-sm mb-4" style={{ color: "var(--foreground)" }}>
            Ask questions about the scraped content. The AI will search through the categorized posts and generate a perspective.
          </p>

          <div className="flex gap-3 items-center mb-4">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={handleKeyPressQuestion}
              placeholder="Ask a question about the scraped content..."
              className="flex-1 px-4 py-3 rounded-lg border-2 text-lg focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors disabled:opacity-50"
              style={{
                backgroundColor: "var(--pastel-yellow)",
                borderColor: "var(--pastel-brown)",
                color: "var(--foreground)",
              }}
              disabled={perspectiveLoading}
            />
            <button
              onClick={handleAskQuestion}
              disabled={perspectiveLoading}
              className="px-6 py-3 rounded-lg font-medium text-lg transition-colors hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: "var(--pastel-pink)",
                color: "var(--foreground)",
              }}
            >
              {perspectiveLoading ? "Thinking..." : "Ask"}
            </button>
          </div>

          {/* Perspective Error */}
          {perspectiveError && (
            <div className="w-full mb-4 p-4 rounded-lg" style={{ backgroundColor: "var(--pastel-pink)" }}>
              <p className="text-red-700 font-medium">Error: {perspectiveError}</p>
            </div>
          )}

          {/* Perspective Results */}
          {perspectiveResults && (
            <div className="w-full space-y-4 p-6 rounded-lg border-2" style={{ backgroundColor: "var(--pastel-brown)", borderColor: "var(--accent-brown)" }}>
              <div>
                <h3 className="text-lg font-semibold mb-2" style={{ color: "var(--foreground)" }}>
                  Question: {perspectiveResults.query}
                </h3>
                <div className="p-4 rounded-lg mt-3" style={{ backgroundColor: "var(--pastel-yellow)" }}>
                  <p className="whitespace-pre-wrap leading-relaxed" style={{ color: "var(--foreground)" }}>
                    {perspectiveResults.perspective}
                  </p>
                </div>
              </div>

              {perspectiveResults.sources && perspectiveResults.sources.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-md font-semibold mb-3" style={{ color: "var(--foreground)" }}>
                    Sources ({perspectiveResults.sources.length}):
                  </h4>
                  <div className="space-y-2">
                    {perspectiveResults.sources.map((source, idx) => (
                      <div key={idx} className="p-3 rounded-lg" style={{ backgroundColor: "var(--pastel-yellow)" }}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium px-2 py-1 rounded" style={{ backgroundColor: "var(--pastel-pink)", color: "var(--foreground)" }}>
                            {source.category}
                          </span>
                          {source.relevance_score && (
                            <span className="text-xs" style={{ color: "var(--foreground)" }}>
                              Relevance: {(source.relevance_score * 100).toFixed(1)}%
                            </span>
                          )}
                        </div>
                        <p className="text-sm" style={{ color: "var(--foreground)" }}>
                          {source.summary}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
