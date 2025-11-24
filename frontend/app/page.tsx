'use client';

import { useState } from 'react';
import SearchBar from '@/components/SearchBar';
import ResultsDisplay from '@/components/ResultsDisplay';

export default function Home() {
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (query: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/recommend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, top_k: 10 }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch recommendations');
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-950 via-purple-900 to-pink-900">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-pink-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute top-1/2 left-1/2 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      <div className="relative z-10 container mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-block mb-4 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full border border-white/20">
            <span className="text-sm text-white/80 font-medium">AI-Powered Assessment Discovery</span>
          </div>
          <h1 className="text-6xl md:text-7xl font-bold text-white mb-6 tracking-tight">
            SHL Assessment
            <span className="block bg-gradient-to-r from-pink-400 via-purple-400 to-indigo-400 bg-clip-text text-transparent">
              Finder
            </span>
          </h1>
          <p className="text-xl text-white/70 max-w-2xl mx-auto">
            Discover the perfect assessment for your hiring needs with intelligent recommendations
          </p>
        </div>

        {/* Search Section */}
        <div className="max-w-4xl mx-auto">
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-8 max-w-4xl mx-auto p-4 bg-red-500/10 backdrop-blur-sm border border-red-500/30 rounded-2xl">
            <p className="text-red-200 text-center">{error}</p>
          </div>
        )}

        {/* Results Section */}
        {results && (
          <div className="mt-12">
            <ResultsDisplay results={results} />
          </div>
        )}

        {/* Empty state */}
        {!results && !loading && !error && (
          <div className="mt-20 text-center text-white/50">
            <svg className="mx-auto h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-lg">Enter a query above to get started</p>
            <p className="text-sm mt-2">Try: "Senior Java developer with strong communication skills"</p>
          </div>
        )}
      </div>
    </div>
  );
}
