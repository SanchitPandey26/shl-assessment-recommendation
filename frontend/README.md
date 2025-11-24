# Frontend Architecture

## Overview

The SHL Assessment Recommendation frontend is a modern, responsive web application built with **Next.js 16** (App Router), **React 19**, and **Tailwind CSS 4**. It provides a clean, intuitive search interface for finding and viewing recommended assessments.

## Technology Stack

- **Framework**: Next.js 16.0.3 with Turbopack
- **React**: 19.2.0
- **Styling**: Tailwind CSS 4
- **TypeScript**: 5.x
- **Package Manager**: npm

## Directory Structure

```
frontend/
├── app/                   # Next.js App Router
│   ├── layout.tsx        # Root layout with metadata
│   ├── page.tsx          # Home page
│   ├── globals.css       # Global styles + Tailwind imports
│   └── favicon.ico       # App icon
├── components/           # React components
│   └── Search.tsx        # Main search interface component
├── public/               # Static assets
├── .next/                # Next.js build output (gitignored)
├── node_modules/         # Dependencies (gitignored)
├── package.json          # Project dependencies
├── tsconfig.json         # TypeScript configuration
└── next.config.ts        # Next.js configuration
```

## Core Components

### 1. Page (`app/page.tsx`)

The home page provides the main layout:

```tsx
<div className="min-h-screen bg-gray-50 dark:bg-gray-900">
  <main className="container mx-auto px-4 py-16">
    <div className="text-center mb-12">
      <h1>SHL Assessment Recommender</h1>
      <p>Find the perfect assessment...</p>
    </div>
    <Search />
  </main>
  <footer>...</footer>
</div>
```

**Features**:

- Centered layout with responsive padding
- Dark mode support via Tailwind
- Hero section with title and description
- Footer with attribution

### 2. Search Component (`components/Search.tsx`)

The main interactive component with three sections:

#### Search Input

```tsx
<form onSubmit={handleSearch}>
  <input
    type="text"
    value={query}
    onChange={(e) => setQuery(e.target.value)}
    placeholder="Describe the role..."
  />
  <button type="submit">Search</button>
</form>
```

**Features**:

- Controlled input with React state
- Loading state during API call
- Disabled state management

#### Error Handling

```tsx
{error && (
  <div className="p-4 bg-red-50 text-red-600">
    {error}
  </div>
)}
```

**Error States**:

- Network errors
- API failures
- Invalid responses

#### Results Display

```tsx
{results && (
  <div className="space-y-6">
    <div>Found {results.total_results} recommendations</div>
    <div className="grid gap-6">
      {results.assessments.map((assessment, index) => (
        <AssessmentCard key={index} assessment={assessment} />
      ))}
    </div>
  </div>
)}
```

**Assessment Card Layout**:

- Title with external link
- Relevance score badge
- Description preview
- Test type tags
- Job level badge
- Relevance reason explanation

## Component Architecture

### State Management

The `Search` component uses React hooks:

```tsx
const [query, setQuery] = useState('');           // User input
const [results, setResults] = useState<SearchResult | null>(null);
const [loading, setLoading] = useState(false);    // Loading state
const [error, setError] = useState('');           // Error messages
const [mounted, setMounted] = useState(false);    // Hydration fix
```

### Hydration Fix

To prevent hydration mismatches (caused by browser extensions injecting attributes), the component only renders after client-side mount:

```tsx
useEffect(() => {
  setMounted(true);
}, []);

if (!mounted) {
  return null;
}
```

This ensures the server-rendered HTML matches the client.

### API Integration

#### API Call Logic

```tsx
const handleSearch = async (e: React.FormEvent) => {
  e.preventDefault();
  
  setLoading(true);
  setError('');
  setResults(null);

  try {
    const response = await fetch('http://localhost:8000/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: 10 }),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch recommendations');
    }

    const data = await response.json();
    setResults(data);
  } catch (err) {
    setError('An error occurred...');
  } finally {
    setLoading(false);
  }
};
```

#### Request Format

```typescript
{
  query: string;      // "Java developer with collaboration"
  top_k: number;      // 10 (default)
}
```

#### Response Format

```typescript
interface SearchResult {
  query: string;
  rewritten_query: string;
  assessments: Assessment[];
  total_results: number;
}

interface Assessment {
  url: string;
  name: string;
  desc: string;
  duration_min: number;
  duration_max: number;
  job_levels: string;
  languages: string[];
  test_types: string[];
  tags: string[];
  relevance_score: number;
  relevance_reason: string;
}
```

## Styling System

### Tailwind CSS Configuration

The project uses **Tailwind CSS 4** with the new `@theme` directive:

```css
@import "tailwindcss";

:root {
  --background: #ffffff;
  --foreground: #171717;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
}
```

### Dark Mode Support

Automatic dark mode based on system preference:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --background: #0a0a0a;
    --foreground: #ededed;
  }
}
```

Classes like `dark:bg-gray-800` automatically adapt.

### Custom Animations

Blob animation for background effects:

```css
@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}

.animate-blob {
  animation: blob 7s infinite;
}
```

## UI Components Breakdown

### Search Bar

- **Input**: Full-width with rounded corners, border, shadow
- **Placeholder**: Helpful example text
- **Button**: Blue gradient, disabled state, loading text

### Assessment Card

- **Layout**: White card with border, rounded corners, hover shadow
- **Header**: Title (linked) + Score badge
- **Body**: Description (2-line clamp)
- **Tags**: Pill-shaped badges for test types and job levels
- **Footer**: Border-top separator with relevance reason

### Color Palette

- **Primary**: Blue (`blue-600`, `blue-700`)
- **Secondary**: Purple/Pink for score badges
- **Neutral**: Gray scale for text and backgrounds
- **Success**: Green for high scores
- **Error**: Red for error messages

## Responsive Design

### Breakpoints

- **Mobile**: `< 768px` - Full width, vertical stack
- **Tablet**: `768px - 1024px` - Adjusted padding, 2-column tags
- **Desktop**: `> 1024px` - Max width container, 4-column metadata grid

### Container Strategy

```tsx
<div className="w-full max-w-4xl mx-auto p-4">
  {/* Content */}
</div>
```

## Performance Optimizations

1. **Client-Side Rendering**: Search component only renders on client (avoids hydration issues)
2. **Controlled Components**: Efficient re-renders with React state
3. **Async/Await**: Non-blocking API calls
4. **Conditional Rendering**: Only render results when available
5. **Turbopack**: Fast development builds with Next.js 16

## Accessibility Features

- **Semantic HTML**: Proper heading hierarchy (`h1`, `h2`, `h3`)
- **Form Labels**: Input has descriptive placeholder
- **Button States**: Disabled state prevents double-submission
- **External Links**: `target="_blank"` with `rel="noopener noreferrer"`
- **Color Contrast**: WCAG AA compliant text/background ratios
- **Focus States**: Visible focus rings on interactive elements

## Development Workflow

### Local Development

```bash
npm run dev
```

- Runs on `http://localhost:3000`
- Hot module replacement (HMR)
- Turbopack for fast rebuilds

### Production Build

```bash
npm run build
npm run start
```

- Optimized static assets
- Server-side rendering (SSR) for initial load
- Client-side navigation after hydration

### Linting

```bash
npm run lint
```

- ESLint with Next.js configuration
- TypeScript type checking

## Future Enhancements

- [ ] Add loading skeleton for better perceived performance
- [ ] Implement pagination for > 10 results
- [ ] Add filter/sort options (duration, job level, test type)
- [ ] Save search history (localStorage)
- [ ] Add "Save to favorites" functionality
- [ ] Implement advanced search with multiple filters
- [ ] Add accessibility improvements (ARIA labels, keyboard navigation)
- [ ] Add analytics tracking (query patterns, click-through rates)

## Deployment Considerations

### Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

Update `Search.tsx`:

```tsx
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

### Build Optimization

- Next.js automatically optimizes images (use `<Image>` component)
- Static generation for marketing pages
- Edge runtime for API routes (if needed)

### CORS

Ensure backend allows frontend domain in production:

```python
allow_origins=["https://your-frontend.com"]
```
