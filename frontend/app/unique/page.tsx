"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

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

interface GenerateResults {
  success: boolean;
  message: string;
  prompt?: string;
  generated_images?: string[];
}

export default function UniquePage() {
  const [question, setQuestion] = useState("");
  const [perspectiveLoading, setPerspectiveLoading] = useState(false);
  const [perspectiveResults, setPerspectiveResults] = useState<PerspectiveResults | null>(null);
  const [perspectiveError, setPerspectiveError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateResults, setGenerateResults] = useState<GenerateResults | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [personName, setPersonName] = useState<string>("");

  // Get person name from URL params or localStorage
  useEffect(() => {
    // Try to get from localStorage (set when navigating from main page)
    const storedName = localStorage.getItem("currentPersonName");
    if (storedName) {
      setPersonName(storedName);
    }
  }, []);

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

  const handleGenerateImages = async () => {
    if (!personName.trim()) {
      setGenerateError("Person name is required. Please search from the main page first.");
      return;
    }

    setGenerating(true);
    setGenerateError(null);
    setGenerateResults(null);

    try {
      const response = await fetch("http://localhost:8000/api/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: personName.trim(),
          number_of_images: 3,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate images");
      }

      const data: GenerateResults = await response.json();
      setGenerateResults(data);
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "An error occurred while generating images");
      console.error("Generate error:", err);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center font-sans" style={{ backgroundColor: "var(--background)" }}>
      <main className="flex min-h-screen w-full max-w-3xl flex-col items-center justify-center py-32 px-16 sm:items-start">
        <div className="w-full mb-8">
          <Link 
            href="/"
            className="inline-block mb-4 px-4 py-2 rounded-lg text-sm font-medium transition-colors hover:opacity-90"
            style={{
              backgroundColor: "var(--pastel-brown)",
              color: "var(--foreground)",
            }}
          >
            ← Back to Search
          </Link>
          
          <h1 className="text-3xl font-bold mb-2" style={{ color: "var(--foreground)" }}>
            Generate Unique Perspective
          </h1>
          <p className="text-sm mb-4" style={{ color: "var(--foreground)" }}>
            Ask questions about the scraped content. The AI will search through the categorized posts and generate a perspective.
          </p>
          
          {/* Generate Images Button */}
          <div className="mb-6">
            <button
              onClick={handleGenerateImages}
              disabled={generating || !personName.trim()}
              className="px-6 py-3 rounded-lg font-medium text-lg transition-colors hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: "var(--accent-brown)",
                color: "var(--background)",
              }}
            >
              {generating ? "Generating Images..." : "Generate Unique Images"}
            </button>
            {!personName.trim() && (
              <p className="text-xs mt-2" style={{ color: "var(--foreground)" }}>
                Note: Please search from the main page first to set the person name.
              </p>
            )}
          </div>
        </div>

        {/* Generate Error */}
        {generateError && (
          <div className="w-full mb-4 p-4 rounded-lg" style={{ backgroundColor: "var(--pastel-pink)" }}>
            <p className="text-red-700 font-medium">Error: {generateError}</p>
          </div>
        )}

        {/* Generate Results */}
        {generateResults && generateResults.success && (
          <div className="w-full mb-8 p-6 rounded-lg border-2" style={{ backgroundColor: "var(--pastel-brown)", borderColor: "var(--accent-brown)" }}>
            <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--foreground)" }}>
              Generated Images
            </h2>
            {generateResults.prompt && (
              <div className="mb-4 p-3 rounded-lg" style={{ backgroundColor: "var(--pastel-yellow)" }}>
                <p className="text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>Prompt:</p>
                <p className="text-sm" style={{ color: "var(--foreground)" }}>{generateResults.prompt}</p>
              </div>
            )}
            {generateResults.generated_images && generateResults.generated_images.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {generateResults.generated_images.map((filename, idx) => (
                  <div key={idx} className="flex flex-col items-center">
                    <img
                      src={`/${filename}`}
                      alt={`Generated image ${idx + 1}`}
                      className="max-w-full h-auto rounded-lg border-2"
                      style={{
                        maxHeight: "400px",
                        borderColor: "var(--pastel-pink)"
                      }}
                    />
                    <p className="text-xs mt-2" style={{ color: "var(--foreground)" }}>
                      Image {idx + 1}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Question/Perspective Section */}
        <div className="w-full">
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

