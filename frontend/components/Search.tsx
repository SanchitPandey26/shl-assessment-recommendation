'use client';

import { useState, useEffect } from 'react';

interface Assessment {
    url: string;
    name: string;
    adaptive_support: string;
    description: string;
    duration: number;
    remote_support: string;
    test_type: string[];
}

interface SearchResult {
    recommended_assessments: Assessment[];
}

export default function Search() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return null;
    }

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError('');
        setResults(null);

        try {
            const response = await fetch(`/api/recommend`, {
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
            setError('An error occurred while fetching recommendations. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full max-w-4xl mx-auto p-4">
            <form onSubmit={handleSearch} className="mb-8">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Describe the role (e.g., 'Java developer with collaboration skills')..."
                        className="flex-1 p-4 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none shadow-sm"
                    />
                    <button
                        type="submit"
                        disabled={loading}
                        className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? 'Searching...' : 'Search'}
                    </button>
                </div>
            </form>

            {error && (
                <div className="p-4 mb-6 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg">
                    {error}
                </div>
            )}

            {results && (
                <div className="space-y-6">
                    <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
                        <p>Found {results.recommended_assessments.length} recommendations</p>
                    </div>

                    <div className="grid gap-6">
                        {results.recommended_assessments.map((assessment, index) => (
                            <div
                                key={index}
                                className="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                                        <a href={assessment.url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-500">
                                            {assessment.name}
                                        </a>
                                    </h3>
                                </div>

                                <p className="text-gray-600 dark:text-gray-300 mb-4">
                                    {assessment.description}
                                </p>

                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                                    <div className="flex items-center gap-2 text-sm">
                                        <span className="font-semibold text-gray-700 dark:text-gray-300">Duration:</span>
                                        <span className="text-gray-600 dark:text-gray-400">{assessment.duration} min</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm">
                                        <span className="font-semibold text-gray-700 dark:text-gray-300">Remote:</span>
                                        <span className="text-gray-600 dark:text-gray-400">{assessment.remote_support}</span>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm">
                                        <span className="font-semibold text-gray-700 dark:text-gray-300">Adaptive:</span>
                                        <span className="text-gray-600 dark:text-gray-400">{assessment.adaptive_support}</span>
                                    </div>
                                </div>

                                <div className="flex flex-wrap gap-2">
                                    {assessment.test_type.map((type, i) => (
                                        <span key={i} className="px-3 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-full">
                                            {type}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
