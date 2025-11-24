import Search from '../components/Search';

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <main className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6 tracking-tight">
            SHL Assessment <span className="text-blue-600">Recommender</span>
          </h1>
          <p className="text-lg md:text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Find the perfect assessment for your role using AI-powered semantic search and reasoning.
          </p>
        </div>

        <Search />
      </main>

      <footer className="text-center py-8 text-gray-500 dark:text-gray-400 text-sm">
        <p>© 2025 SHL Assessment Recommender. Powered by Gemini & Hybrid Search.</p>
      </footer>
    </div>
  );
}
