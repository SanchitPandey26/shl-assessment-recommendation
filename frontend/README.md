# SHL Assessment Recommender - Frontend

A modern, responsive web interface built with **Next.js 16** and **TailwindCSS** for the Assessment Recommendation Engine.

## Features

* **Semantic Search Interface**: Clean input for natural language queries.
* **Real-time Results**: Displays recommendations with AI-generated reasoning.
* **Rich Assessment Cards**: Shows duration, test type, and key skills.
* **Adaptive Theme**: Dark/Light mode support.
* **API Integration**: Connects to FastAPI backend with robust error handling.

## Tech Stack

* **Framework**: Next.js 16 (App Router)
* **Language**: TypeScript
* **Styling**: Tailwind CSS
* **Icons**: Heroicons
* **State Management**: React Hooks

## Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Create a `.env.local` file (optional, defaults to localhost:8000):

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000   #Default API URL
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

## Structure

```
frontend/
├── app/
│   ├── page.tsx           # Main Search Page
│   ├── layout.tsx         # Root Layout (Fonts, metadata)
│   └── globals.css        # Tailwind directives
├── components/
│   ├── Search.tsx         # Search Logic Container
│   ├── SearchBar.tsx      # Input Component
│   ├── ResultsDisplay.tsx # List of Assessment Cards
│   └── ServerStatusProvider.tsx # Health check context
└── public/                # Static assets
```

## API Integration

The frontend expects the backend to be running at `http://localhost:8000`.
It sends POST requests to `/recommend`:

```typescript
// Payload
{
  "query": "Java developer test",
  "top_k": 10
}
```

And receives:

```json
{
  "recommended_assessments": [
    {
      "name": "Automata Fix - Java",
      "description": "...",
      "duration": 45,
      "adaptive_support": "Yes",
      "relevance_reason": "Matches 'Java' skill and duration..."
    }
  ]
}
```
