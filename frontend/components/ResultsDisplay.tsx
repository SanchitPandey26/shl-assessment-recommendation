'use client';

interface Assessment {
    url: string;
    name: string;
    desc: string;
    duration_min?: number;
    duration_max?: number;
    job_levels?: string;
    languages?: string[];
    test_types?: string[];
    tags?: string[];
    relevance_score?: number;
    relevance_reason?: string;
}

interface ResultsDisplayProps {
    results: {
        query: string;
        rewritten_query: string;
        assessments: Assessment[];
        total_results: number;
    };
}

export default function ResultsDisplay({ results }: ResultsDisplayProps) {
    return (
        <div className="max-w-6xl mx-auto">
            {/* Query Info */}
            <div className="mb-8 p-6 bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl">
                <p className="text-sm text-white/60 mb-2">
                    <span className="font-semibold">Your query:</span> {results.query}
                </p>
                <p className="text-sm text-white/80">
                    <span className="font-semibold">Enhanced to:</span> {results.rewritten_query}
                </p>
            </div>

            {/* Results Header */}
            <h2 className="text-3xl font-bold text-white mb-8">
                {results.total_results} Recommended Assessment{results.total_results !== 1 ? 's' : ''}
            </h2>

            {/* Results List */}
            <div className="space-y-4">
                {results.assessments.map((assessment, index) => (
                    <div
                        key={assessment.url}
                        className="group relative bg-white/95 backdrop-blur-md border border-gray-200 rounded-2xl p-6 hover:shadow-2xl transition-all duration-300 hover:scale-[1.02]"
                    >
                        {/* Rank badge */}
                        <div className="absolute -left-3 -top-3 w-12 h-12 bg-gradient-to-br from-purple-600 to-pink-600 rounded-full flex items-center justify-center shadow-lg">
                            <span className="text-white font-bold text-lg">{index + 1}</span>
                        </div>

                        {/* Header  */}
                        <div className="flex items-start justify-between mb-4 ml-6">
                            <div className="flex-1">
                                <a
                                    href={assessment.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-2xl font-bold text-gray-900 hover:text-purple-600 transition-colors flex items-center gap-2 group/link"
                                >
                                    {assessment.name || 'Unnamed Assessment'}
                                    <svg className="w-5 h-5 opacity-0 group-hover/link:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                    </svg>
                                </a>
                            </div>
                            {assessment.relevance_score !== undefined && (
                                <div className="shrink-0 ml-4">
                                    <div className="px-4 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-full font-bold shadow-md">
                                        {(assessment.relevance_score * 100).toFixed(0)}% Match
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Description */}
                        {assessment.desc && (
                            <p className="text-gray-700 mb-4 ml-6 text-lg">{assessment.desc}</p>
                        )}

                        {/* Relevance Reason */}
                        {assessment.relevance_reason && (
                            <div className="mb-6 ml-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 border-l-4 border-orange-400 rounded-lg">
                                <div className="flex items-start gap-2">
                                    <svg className="w-5 h-5 text-orange-600 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                    </svg>
                                    <p className="text-sm text-gray-800 flex-1">
                                        <span className="font-semibold text-orange-900">Why this matches:</span> {assessment.relevance_reason}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Metadata Grid */}
                        <div className="ml-6 grid grid-cols-2 md:grid-cols-4 gap-4">
                            {(assessment.duration_min || assessment.duration_max) && (
                                <div className="flex items-center gap-2 p-3 bg-purple-50 rounded-lg">
                                    <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <div>
                                        <p className="text-xs text-purple-600 font-medium">Duration</p>
                                        <p className="text-sm font-semibold text-gray-900">
                                            {assessment.duration_min && assessment.duration_max
                                                ? `${assessment.duration_min}-${assessment.duration_max} min`
                                                : `${assessment.duration_min || assessment.duration_max} min`}
                                        </p>
                                    </div>
                                </div>
                            )}
                            {assessment.job_levels && (
                                <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
                                    <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                                    </svg>
                                    <div>
                                        <p className="text-xs text-blue-600 font-medium">Job Level</p>
                                        <p className="text-sm font-semibold text-gray-900">{assessment.job_levels || 'Any'}</p>
                                    </div>
                                </div>
                            )}
                            {assessment.languages && assessment.languages.length > 0 && (
                                <div className="flex items-center gap-2 p-3 bg-green-50 rounded-lg">
                                    <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                                    </svg>
                                    <div>
                                        <p className="text-xs text-green-600 font-medium">Languages</p>
                                        <p className="text-sm font-semibold text-gray-900">{assessment.languages.join(', ')}</p>
                                    </div>
                                </div>
                            )}
                            {assessment.test_types && assessment.test_types.length > 0 && (
                                <div className="flex items-center gap-2 p-3 bg-pink-50 rounded-lg">
                                    <svg className="w-5 h-5 text-pink-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <div>
                                        <p className="text-xs text-pink-600 font-medium">Test Types</p>
                                        <p className="text-sm font-semibold text-gray-900">{assessment.test_types.slice(0, 2).join(', ')}</p>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Tags */}
                        {assessment.tags && assessment.tags.length > 0 && (
                            <div className="mt-4 ml-6">
                                <div className="flex flex-wrap gap-2">
                                    {assessment.tags.slice(0, 6).map((tag, i) => (
                                        <span key={i} className="px-3 py-1 bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 rounded-full text-sm font-medium">
                                            #{tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
