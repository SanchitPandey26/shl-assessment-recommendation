# Backend - SHL Assessment Recommender

AI-powered backend API that uses **Google Gemini** for reasoning, embeddings, and reranking.

## Architecture

A lightweight, API-centric architecture that removed heavy dependencies (Torch/ChromaDB).

```
[FastAPI] -> [KeyManager] -> [Query Rewriter (Gemini)]
              |
              v
[Hybrid Retriever] --> [Gemini Embeddings] + [TF-IDF]
           |
           v
[LLM Reranker] --> [Gemini] --> [Final JSON Response]
```

## Key Features

* **Key Rotation (`key_manager.py`)**: Rotates 3+ Gemini API keys to handle strict rate limits (5 RPM).
* **Proactive Rate Limiting**: Intelligent `sleep()` pacing between calls.
* **Vector Search**: Pre-computed `.npy` embeddings (loaded in ~50ms).
* **No Heavy ML Libs**: Runs on standard Python CPU environments (Render/Vercel compatible).

## Setup & Run

### 1. Environment

Ensure your `.env` has:

```ini
GEMINI_API_KEY_1="..."
GEMINI_API_KEY_2="..."
GEMINI_API_KEY_3="..."
EMBEDDING_MODEL="models/gemini-embedding-001"
# ... (see root README for full list)
```

### 2. Install

```bash
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

### 3. Generate Data (If needed)

If you modified the catalog, regenerate embeddings:

```bash
python embeddings/generate_embeddings.py
# Creates data/embeddings_gemini.npy
```

### 4. Run Server

```bash
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`.

## Directory Map

* `app/`: API logic (endpoints, retriever wrapper, key manager).
* `embeddings/`: Core search engine (NumPy vector search, TF-IDF).
* `llm/`: Prompts and logic for Gemini interaction (Rewrite/Rerank).
* `data/`: Static data files (`.json`, `.npy`).
* `eval/`: Evaluation scripts to benchmark Recall@10.

## Testing

Run the evaluation suite:

```bash
python eval/eval_llm_enhanced.py
```

This runs the full pipeline against `data/train_test/Gen_AI Dataset.xlsx` and outputs metrics.
