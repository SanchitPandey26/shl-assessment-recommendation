# SHL Assessment Recommendation System

An AI-powered recommendation system that helps match job roles to the most relevant SHL assessments using **hybrid retrieval** (semantic + lexical search) and **LLM-based reranking**.

## Features

- 🔍 **Hybrid Search**: Combines vector embeddings (BGE) with TF-IDF for comprehensive matching
- 🤖 **LLM Reranking**: Uses Gemini to intelligently rank results based on requirement coverage
- ⚡ **Fast Response**: ~2s end-to-end latency for top 10 recommendations
- 🎯 **Adaptive Boosting**: Query-aware score adjustments for better precision
- 📊 **Current Recall@10**: 0.51 (51% of correct tests in top 10 results)
- 🌐 **Modern UI**: Next.js 16 + React 19 + Tailwind CSS 4

## Architecture Overview

```
┌─────────────┐
│   Frontend  │  Next.js 16 + React 19
│  (Port 3000)│
└──────┬──────┘
       │ HTTP POST /recommend
       ▼
┌─────────────────────────────────────────┐
│          FastAPI Backend                │
│           (Port 8000)                   │
├─────────────────────────────────────────┤
│  1. Query Rewriter (Gemini)             │
│     ↓                                   │
│  2. Hybrid Retriever (40 candidates)    │
│     - Vector Search (BGE embeddings)    │
│     - Lexical Search (TF-IDF)           │
│     - Adaptive Boosting                 │
│     ↓                                   │
│  3. LLM Reranker (Gemini)               │
│     ↓                                   │
│  4. Top 10 Results                      │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│   Data Layer        │
│  - 377 Assessments  │
│  - Embeddings       │
│  - Metadata         │
└─────────────────────┘
```

## Project Structure

```
shl-assessment-recommendation/
├── backend/                 # FastAPI backend
│   ├── app/                # API endpoints
│   ├── embeddings/         # Retrieval engine
│   ├── llm/                # LLM components
│   ├── scraper/            # Data cleaning
│   ├── eval/               # Evaluation scripts
│   └── data/               # Embeddings & metadata
├── frontend/               # Next.js frontend
│   ├── app/               # Pages and layouts
│   └── components/        # React components
└── README.md              # This file
```

## Prerequisites

- **Python**: 3.10+
- **Node.js**: 18+
- **API Key**: Google Gemini API key

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd shl-assessment-recommendation
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
cd backend
python -m venv .venv
```

#### Activate Virtual Environment

**Windows**:

```bash
.venv\Scripts\activate
```

**macOS/Linux**:

```bash
source .venv/bin/activate
```

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
GEMINI_API_KEY=your_api_key_here
```

To get a Gemini API key:

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste it into `.env`

#### Generate Embeddings (First Time Setup)

```bash
# Clean the catalog
python scraper/clean_catalog.py

# Generate embeddings (takes ~2-3 minutes)
python embeddings/generate_embeddings.py

# Build vector store for deployment (optional)
python embeddings/build_vectorstore.py
```

#### Start Backend Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Backend will be available at:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:3000`

## Usage

### Search Interface

1. Open `http://localhost:3000` in your browser
2. Enter a job description (e.g., *"Java developer with collaboration skills, under 40 minutes"*)
3. Click **Search**
4. View top 10 recommended assessments with:
   - Relevance score
   - Test description
   - Duration, languages, job levels
   - Reason for recommendation

### API Usage

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Java developer with collaboration skills",
    "top_k": 10
  }'
```

Response:

```json
{
  "query": "Java developer with collaboration skills",
  "rewritten_query": "Java developer collaboration",
  "assessments": [
    {
      "url": "https://www.shl.com/products/...",
      "name": "Automata Fix (New)",
      "desc": "Hands-on Java debugging and fixing...",
      "relevance_score": 0.95,
      "relevance_reason": "Directly tests Java coding skills..."
    }
  ],
  "total_results": 10
}
```

## Testing & Evaluation

### Run Recall Evaluation

```bash
cd backend
python -m eval.eval_llm_enhanced
```

This evaluates the system against a ground truth dataset and calculates **Recall@10**.

**Current Performance**:

- **Recall@10**: 0.49
- **Mean latency**: ~2s per query

### Test Single Query

```bash
cd backend
python test_llm_pipeline.py
```

This runs a single test query through the full pipeline and displays:

- Retrieved candidates
- Reranking results
- Relevance scores and reasons

## Development

### Backend Development

See [backend/README.md](backend/README.md) for detailed architecture documentation.

**Key files**:

- `app/main.py`: API endpoints
- `embeddings/hybrid_retriever.py`: Core retrieval logic
- `llm/llm_reranker.py`: LLM-based reranking
- `llm/assessment_type_rules.py`: Test categorization

### Frontend Development

See [frontend/README.md](frontend/README.md) for detailed architecture documentation.

**Key files**:

- `app/page.tsx`: Home page layout
- `components/Search.tsx`: Main search interface

### Running in Development Mode

**Backend** (with auto-reload):

```bash
cd backend
.venv\Scripts\activate  # or source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend** (with hot reload):

```bash
cd frontend
npm run dev
```

## Configuration

### Backend Configuration

Edit `backend/embeddings/generate_embeddings.py` to change the embedding model:

```python
# Current: BGE Small (384-dim, faster)
MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Alternative: BGE Base (768-dim, more accurate)
# MODEL_NAME = "BAAI/bge-base-en-v1.5"
```

After changing, regenerate embeddings:

```bash
python embeddings/generate_embeddings.py
```

### Frontend Configuration

For production, create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

Update `components/Search.tsx`:

```tsx
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

## Deployment

### Backend Deployment

1. **Set up environment**:
   - Python 3.10+ runtime
   - Install dependencies: `pip install -r requirements.txt`
   - Set `GEMINI_API_KEY` environment variable

2. **Copy required files**:
   - `app/`, `embeddings/`, `llm/`, `scraper/`
   - `data/embeddings_bge_small.npy`
   - `data/meta_bge_small.json`
   - `data/shl_catalog_clean.json`
   - `vector_store_bge_small/` (if using ChromaDB)

3. **Run with production server**:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

### Frontend Deployment

1. **Build production bundle**:

   ```bash
   cd frontend
   npm run build
   ```

2. **Deploy to Vercel** (recommended):

   ```bash
   npm install -g vercel
   vercel
   ```

3. **Or use any Node.js hosting**:

   ```bash
   npm run start
   ```

4. **Update CORS** in `backend/app/main.py`:

   ```python
   allow_origins=["https://your-frontend-domain.com"]
   ```

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Recall@10** | 0.49 | 49% of correct tests in top 10 |
| **Retrieval Time** | ~200ms | Hybrid search (40 candidates) |
| **Reranking Time** | ~1-2s | LLM call to Gemini |
| **Total Latency** | ~1.5-2.5s | End-to-end per query |
| **Catalog Size** | 377 tests | SHL assessment catalog |
| **Embedding Model** | BGE-small | 384-dim embeddings |

## Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'sentence_transformers'`

```bash
pip install -r requirements.txt
```

**Problem**: `File not found: embeddings_bge_small.npy`

```bash
python embeddings/generate_embeddings.py
```

**Problem**: `API key not found`

```bash
# Create .env file in backend/
echo "GEMINI_API_KEY=your_key" > .env
```

### Frontend Issues

**Problem**: `Cannot connect to backend`

- Ensure backend is running on port 8000
- Check CORS settings in `backend/app/main.py`

**Problem**: Hydration mismatch warnings

- These are usually caused by browser extensions
- The app includes a fix (`mounted` state check)
- Disable extensions or use incognito mode

## Future Improvements

### Backend

- [ ] Increase catalog enrichment (currently 43/377 tests enriched)
- [ ] Implement multi-criteria scoring (coverage + complementarity)
- [ ] Add query expansion for better recall
- [ ] Cache LLM responses for common queries
- [ ] Implement feedback loop for relevance tuning

### Frontend

- [ ] Add loading skeleton for better UX
- [ ] Implement pagination for > 10 results
- [ ] Add filter/sort options (duration, type, level)
- [ ] Save search history (localStorage)
- [ ] Add "Save to favorites" functionality

## License

[Add your license here]

## Contact

[Add contact information]

## Acknowledgments

- **SHL**: Assessment catalog and dataset
- **BGE Embeddings**: BAAI/bge-small-en-v1.5
- **Google Gemini**: LLM for reranking and query rewriting
- **Next.js**: React framework
- **FastAPI**: Python web framework
