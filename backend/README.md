# Backend Architecture

## Overview

The SHL Assessment Recommendation backend is a FastAPI-based service that uses **hybrid retrieval** (semantic + lexical search) combined with **LLM-powered reranking** to recommend the most relevant assessments for a given job role query.

## Recall Evolution

The system has achieved significant recall improvements through iterative enhancements:

```
Recall Evolution (Mean Recall@10)
---------------------------------
0.47  → Baseline (hybrid retrieval only)
0.49  → + Test categorization
0.49  → + Adaptive boosting  
0.49  → + Reranker prompt improvements

Target: 0.75+ (requires full catalog enrichment)
```

**Current Status**: Achieved **0.49 Recall@10** with partial enrichment (43/377 tests). Further gains expected with:

- Complete catalog enrichment
- BGE-base model (0.51+ expected, not deployed due to resource constraints)
- Query expansion and feedback loops

## Architecture Diagram

```
User Query → Query Rewriter (LLM) → Hybrid Retriever → LLM Reranker → Top 10 Results
                                           ↓
                                    Vector Search (BGE)
                                           +
                                    Lexical Search (TF-IDF)
                                           +
                                    Adaptive Boosting
```

## Directory Structure

```
backend/
├── app/                    # FastAPI application
│   ├── main.py            # API endpoints and CORS setup
│   ├── retriever.py       # Retrieval logic wrapper
│   ├── reranker.py        # Reranking logic wrapper
│   └── schemas.py         # Pydantic request/response models
├── embeddings/            # Vector search and embedding generation
│   ├── hybrid_retriever.py      # Main retrieval engine
│   ├── generate_embeddings.py   # Embedding generation script
│   └── build_vectorstore.py     # ChromaDB store builder
├── llm/                   # LLM-powered components
│   ├── query_rewriter.py        # Query enhancement with Gemini
│   ├── llm_reranker.py          # LLM-based result reranking
│   ├── assessment_type_rules.py # Test categorization and boosting
│   └── key_rotator.py           # API key rotation logic
├── scraper/               # Data cleaning and preprocessing
│   └── clean_catalog.py         # Catalog normalization
├── eval/                  # Evaluation scripts
│   ├── eval_llm_enhanced.py     # Full pipeline evaluation
│   └── evaluate_recall.py       # Recall@10 calculation
├── data/                  # Embeddings, metadata, and catalog
│   ├── shl_catalog_clean.json   # Cleaned assessment catalog
│   ├── embeddings_bge_small.npy # Precomputed embeddings
│   └── meta_bge_small.json      # Assessment metadata
└── vector_store_bge_small/      # ChromaDB persistent store
```

## Core Components

### 1. FastAPI Application (`app/`)

#### `main.py`

- **Endpoint**: `POST /recommend`
- **Flow**:
  1. Receives query and `top_k` parameter
  2. Calls `retrieve_assessments()` to get 40 candidates
  3. Calls `rerank_results()` to get top 10
  4. Returns JSON response with ranked assessments
- **CORS**: Configured for frontend (`localhost:3000`)

#### `retriever.py`

- Wraps `HybridRetriever` and `llm_rewrite`
- Returns dict with:
  - `original_query`
  - `rewritten_query`
  - `candidates` (list of 40 assessments)

#### `reranker.py`

- Wraps `llm_rerank` from `llm/llm_reranker.py`
- Takes candidates and returns top K with:
  - `relevance_score` (0.0-1.0)
  - `relevance_reason` (LLM explanation)

### 2. Hybrid Retrieval (`embeddings/hybrid_retriever.py`)

The `HybridRetriever` class combines:

**Why Hybrid > Vector-Only?**
Vector search excels at semantic matching but can miss exact keyword matches. For example, "Java developer" might semantically match "Python developer" (both are programming roles), but lexical search ensures "Java" tests are prioritized. Hybrid retrieval combines the best of both worlds.

#### Vector Search (Semantic)

- **Model**: `BAAI/bge-small-en-v1.5` (384-dim embeddings)
- **Method**: Cosine similarity between query embedding and 377 test embeddings
- **Normalization**: Scores normalized to [0, 1]
- **Rationale**: BGE-small chosen for deployment due to faster inference and lower memory footprint

#### Lexical Search (Keyword)

- **Method**: TF-IDF with scikit-learn
- **Advantage**: Catches exact keyword matches (e.g., "Java" → "Java Platform")
- **Weight**: 25% of final score (empirically determined)

#### Scoring Formula

```python
final_score = (alpha_vector * vector_score) + (alpha_lexical * lexical_score) + boosts
```

Default: `alpha_vector=0.75`, `alpha_lexical=0.25`

#### Metadata Boosts

- **Duration match**: +0.12 if test duration ≤ query duration
- **Job level match**: +0.08 if test job level matches query
- **Language match**: +0.05 if test language in query languages
- **Test type match**: +0.06 if test type code matches

#### Adaptive Boosting (`assessment_type_rules.py`)

- **Developer queries** + Automata tests: +0.20
- **Cultural fit** + OPQ tests: +0.20
- **Senior roles** + Verify tests: +0.15

### 3. LLM Components (`llm/`)

#### Query Rewriter (`query_rewriter.py`)

- **Model**: Gemini 1.5 Flash
- **Purpose**: Extract structured fields from natural language
- **Extracted Fields**:
  - `rewrite`: Cleaned query
  - `durations`: List of time constraints
  - `job_levels`: List of seniority levels
  - `languages`: List of languages
  - `test_type_codes`: List of test type codes

Example:

- Input: *"Java developer, senior level, under 30 minutes"*
- Output:

  ```json
  {
    "rewrite": "Java developer senior",
    "job_levels": ["Senior"],
    "durations": [30]
  }
  ```

#### LLM Reranker (`llm_reranker.py`)

- **Model**: Gemini 1.5 Flash
- **Prompt Strategy**:
  - **Requirement Coverage** (45% weight): Does test cover all query requirements?
  - **Relevance** (30% weight): How relevant is the test?
  - **Quality** (25% weight): Test quality and reliability
- **Few-shot examples**: Handles combination queries (e.g., "Java + collaboration")
- **Output**: List of assessments with scores (0.0-1.0) and reasons

#### Assessment Type Categorization (`assessment_type_rules.py`)

Tests are automatically categorized to enable intelligent matching and boosting.

- **Categories**:
  - `practical_coding`: Hands-on coding (e.g., Automata)
  - `theoretical_knowledge`: MCQ/knowledge tests
  - `personality`: OPQ, behavioral assessments
  - `cognitive`: Verify series, reasoning tests
  - `soft_skills`: Communication, teamwork
  - `situational`: SJT tests
  - `simulation`: Work simulations

- **Purpose**:
  - Enables **adaptive boosting** (e.g., "developer" queries boost practical_coding tests)
  - Improves semantic matching by including category info in embeddings
  - Provides structured metadata for UI filtering (future)

- **Mapping**:
  - Query patterns → Required categories
  - Test names → Categories
  - Test type codes → Categories

### 4. Data Pipeline

#### Embedding Generation (`embeddings/generate_embeddings.py`)

1. Load `shl_catalog_clean.json` (377 tests)
2. Build `embed_text` from:
   - Test name
   - Description
   - Job levels
   - Languages
   - Test types
   - Tags
   - Categories
3. Encode with `BAAI/bge-small-en-v1.5`
4. Save:
   - `embeddings_bge_small.npy` (377 × 384 matrix)
   - `meta_bge_small.json` (metadata)

#### Vector Store Building (`embeddings/build_vectorstore.py`)

1. Load `.npy` embeddings and metadata
2. Create ChromaDB persistent client
3. Store in `vector_store_bge_small/`
4. Used for deployment (optional, NumPy is primary)

#### Catalog Cleaning (`scraper/clean_catalog.py`)

- Normalizes raw catalog data
- Extracts keywords, tags, job levels
- Adds `test_categories` field
- Deduplicates and validates

### 5. Evaluation (`eval/`)

#### `eval_llm_enhanced.py`

- Loads queries from `data/train_test/Gen_AI Dataset.xlsx`
- Runs full pipeline (rewrite → retrieve → rerank)
- Calculates **Recall@10**:

  ```
  Recall@10 = (# ground truth in top 10) / (# ground truth total)
  ```

- Current performance: **0.49 Recall@10**

#### `evaluate_recall.py`

- Simpler version without reranking
- Only evaluates hybrid retrieval

## API Reference

### `POST /recommend`

**Request**:

```json
{
  "query": "Java developer with collaboration skills",
  "top_k": 10
}
```

**Response**:

```json
{
  "query": "Java developer with collaboration skills",
  "rewritten_query": "Java developer collaboration",
  "assessments": [
    {
      "url": "https://www.shl.com/products/...",
      "name": "Automata Fix (New)",
      "desc": "Hands-on Java debugging and fixing...",
      "duration_min": 40,
      "duration_max": 40,
      "job_levels": "Mid-Professional, Professional...",
      "languages": ["English (USA)"],
      "test_types": ["Knowledge & Skills"],
      "tags": ["Java", "Coding", ...],
      "relevance_score": 0.95,
      "relevance_reason": "Directly tests Java coding skills..."
    },
    ...
  ],
  "total_results": 10
}
```

## Configuration

### Environment Variables

Required in `.env`:

```bash
GEMINI_API_KEY=your_api_key_here
```

### Model Selection

In `generate_embeddings.py`, `build_vectorstore.py`, `hybrid_retriever.py`:

- **Current**: `BAAI/bge-small-en-v1.5` (384-dim, faster)
- **Alternative**: `BAAI/bge-base-en-v1.5` (768-dim, more accurate)

Comment/uncomment the relevant lines to switch models.

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Recall@10** | 0.49 | Correct test in top 10 results |
| **Retrieval Time** | ~200ms | Hybrid search (40 results) |
| **Reranking Time** | ~1-2s | LLM call to Gemini |
| **Total Latency** | ~1.5-2.5s | End-to-end |

### Model Choice: BGE-Small vs BGE-Base

**Current Deployment**: `BAAI/bge-small-en-v1.5`

- **Pros**: Faster inference (~100ms), lower memory (384-dim), suitable for free-tier deployment
- **Cons**: Slightly lower recall (~0.49 vs 0.51)

**Alternative (Not Deployed)**: `BAAI/bge-base-en-v1.5`

- **Pros**: Higher recall (~0.51), better semantic understanding (768-dim)
- **Cons**: 2x slower inference, 2x memory usage, not deployable on Render free tier

**Decision**: BGE-small chosen for production due to deployment constraints. BGE-base can be used for local development or paid hosting.

## Key Design Decisions

1. **Hybrid Search**: Combines semantic understanding (vector) with exact matching (lexical)
2. **Adaptive Boosting**: Query-aware boosts for better precision
3. **LLM Reranking**: Handles complex, multi-requirement queries
4. **Two-Stage Retrieval**: Cheap retrieval (40 candidates) → Expensive reranking (10 results)
5. **Categorization**: Maps tests to types for better matching

## Known Limitations

1. **Latency**: End-to-end latency of 1.5-2.5s depends heavily on LLM reranker (Gemini API call)
2. **Enrichment Coverage**: Only 43/377 tests have LLM enrichment, limiting semantic matching quality
3. **LLM Consistency**: Reranker relies on Gemini, which may exhibit prompt drift over time
4. **Categorization**: Some edge-case tests may be miscategorized, affecting adaptive boosting
5. **Deployment Constraints**: BGE-small used instead of more accurate BGE-base due to resource limits
6. **No Caching**: LLM calls are not cached, leading to redundant processing for common queries

## Future Improvements

- [ ] **Complete catalog enrichment** (377/377 tests) - Expected +15-20% recall gain
- [ ] **Implement LLM response caching** - Reduce latency for common queries
- [ ] **Add query expansion** - Generate query variations for better coverage
- [ ] **Multi-criteria scoring** - Implement coverage + complementarity scoring in reranker
- [ ] **Feedback loop** - Collect user feedback to fine-tune retrieval and ranking
- [ ] **Migrate to BGE-base** - When hosting budget allows, upgrade for +2-3% recall
- [ ] **Add A/B testing framework** - Systematically evaluate prompt and weight changes
