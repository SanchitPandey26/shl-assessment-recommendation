# SHL Assessment Recommendation Engine (AI-Powered)

An advanced Recommendation System for SHL assessments that uses **Hybrid Search (Vector + Keyword)** and **LLM-based Reasoning (Reranking)** to find the best tests for a job description.

> **Architecture**: accurate, lightweight, and cost-effective using Google Gemini API directly. No local vector DB or heavy ML libraries required.

---

## Key Features

* **Hybrid Retrieval**: Combines **Semantic Search** (Gemini Embeddings) + **Keyword Search** (TF-IDF) for maximum recall.
* **LLM Reranking**: Uses **Gemini 2.5 Flash** to reason about "why" a test fits a query, filtering out irrelevant vector matches.
* **Query Expansion**: Automatically rewrites user queries (e.g., "Java dev" -> "Hands-on Java coding assessment for java developers") for better search results.
* **Smart Metadata Filtering**: Boosts scores based on duration, job level, and test type constraints.
* **Key Rotation & Rate Limiting**: Built-in `KeyManager` rotates between multiple Gemini API keys to handle rate limits (5 RPM per key) gracefully.
* **Lightweight Deployment**: Used Numpy instead of Vector DB to store embeddings to reduce memory usage. Embeddings are pre-computed (`.npy`) and loaded in-memory (~2MB).

---

## Tech Stack

### Backend

* **Language**: Python 3.10+
* **Framework**: FastAPI (Async)
* **AI Models**: Google GenAI SDK (`google-genai`)
  * *Embedding*: `models/gemini-embedding-001`
  * *Reranking/Rewrite*: `gemini-2.5-flash`
* **Search**: Scikit-Learn (TF-IDF, Cosine Similarity) + NumPy
* **Data**: JSON / NPY (embedded catalog)

### Frontend

* **Framework**: Next.js 16 (React 19)
* **Styling**: TailwindCSS
* **State**: React Hooks (SWR/Fetch)

---

## Setup & Installation

### 1. Prerequisites

* Python 3.10+
* Node.js 18+
* **Google Gemini API Keys** (At least 1, recommended 3 for rotation)

### 2. Backend Setup

```bash
cd backend

# Create venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows

# Install dependencies (lightweight)
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

**Configure `.env`**:

```ini
# API Keys (Rotate for higher throughput)
GEMINI_API_KEY_1="your_key_1"
GEMINI_API_KEY_2="your_key_2"
GEMINI_API_KEY_3="your_key_3"

# Models
EMBEDDING_MODEL="models/gemini-embedding-001"
REWRITE_MODEL="gemini-2.5-flash"
RERANK_MODEL="gemini-2.5-flash"
```

### 3. Data Preparation (One-Time)

Pre-compute embeddings using Gemini:

```bash
# 1. Scrape/Prepare catalog (optional if meta_gemini.json exists)
python scraper/clean_catalog.py

# 2. Generate Embeddings (Cost: Free tier friendly, strict pacing)
python embeddings/generate_embeddings.py
# Output: data/embeddings_gemini.npy
```

### 4. Run Servers

**Backend**:

```bash
uvicorn app.main:app --reload
# Health check: http://localhost:8000/health
```

**Frontend**:

```bash
cd frontend
npm install
npm run dev
```

---

## How It Works (Architecture)

1. **User Query**: "I need a Java test for a senior dev, 40 mins max."
2. **Key Rotation**: Backend `KeyManager` selects an active API key.
3. **LLM Rewrite**:
    * *Input*: "Java test senior 40 mins"
    * *Output*: `{"rewrite": "Advanced Java programming assessment for Senior Developer, duration < 40mins", "filters": {"duration": 40, "level": "senior"}}`
4. **Hybrid Search**:
    * **Vector**: Embeds rewritten query -> Cosine similarity against `embeddings_gemini.npy`.
    * **Lexical**: TF-IDF match against name/description.
    * **Metadata**: Boost score if duration <= 40 and job_level matches.
5. **LLM Rerank**:
    * Top 20 candidates are sent to Gemini Flash.
    * Prompt: "Rank these tests for a Senior Java Developer. Prioritize hands-on coding."
    * Output: Top 10 JSON results with "Reasoning".
6. **Response**: Frontend displays ranked assessments.

---

## Evaluation Metrics

We benchmark recall performance using an annotated dataset (`eval/Gen_AI Dataset.xlsx`).

| Method | Mean Recall@10 | Notes |
| :--- | :--- | :--- |
| **Hybrid Baseline** | 0.373 | Vector + Keyword only |
| **LLM Enhanced** | **~0.65+** | With Query Rewrite & Reranking |

To run eval:

```bash
python eval/eval_llm_enhanced.py
```

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entrypoint
│   │   ├── key_manager.py   # API Key Rotation Logic
│   │   ├── retriever.py     # Retrieval Orchestrator
│   │   └── reranker.py      # Reranking Logic
│   ├── embeddings/
│   │   ├── hybrid_retriever.py # Core search engine (NumPy/Sklearn)
│   │   └── generate_embeddings.py
│   ├── llm/
│   │   ├── query_rewriter.py # Query expansion
│   │   └── llm_reranker.py   # Re-ranking prompt
│   └── data/                 # Store for .npy and .json files
└── frontend/
    ├── components/          # React UI Components
    └── app/                 # Next.js Pages
```

## Known Limits

* **Rate Limits**: Free tier Gemini has 5 RPM. The `KeyManager` + `sleep()` strategy handles this but latency per request is ~3-5s.
* **Context Window**: Reranking huge lists (e.g., 50+ candidates) may hit token limits; currently capped at Top 20.

---
**Author**: Sanchit Pandey
