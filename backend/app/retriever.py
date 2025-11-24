import sys
from pathlib import Path

# Ensure import paths
sys.path.append(str(Path(__file__).resolve().parents[1]))

from embeddings.hybrid_retriever import HybridRetriever
from llm.query_rewriter import llm_rewrite

# ---------------------------------------------------------
# Lazy-loaded retriever instance (RENDER SAFE)
# ---------------------------------------------------------
_retriever = None

def get_retriever():
    """
    Lazy-load HybridRetriever to avoid heavy initialization
    when the module is imported. Critical for Render 512MB.
    """
    global _retriever
    if _retriever is None:
        print("⚡ Initializing HybridRetriever (cold start)...")
        _retriever = HybridRetriever()
    return _retriever


# ---------------------------------------------------------
# Main public function
# ---------------------------------------------------------
def retrieve_assessments(query: str, top_k: int = 40):
    """
    Full retrieval pipeline:
    1. LLM-based query rewrite
    2. Hybrid retrieval using vector + lexical + boosting
    """
    try:
        # Step 1 — Rewrite using LLM (fallback regex enabled)
        parsed = llm_rewrite(query, fallback=True)
        rewritten_query = parsed["rewrite"]

        # Step 2 — Retrieve from hybrid retriever
        retriever = get_retriever()
        candidates = retriever.retrieve(rewritten_query, top_k=top_k)

        # Step 3 — Prepare candidates for reranker
        formatted_candidates = []
        for c in candidates:
            meta = c["meta"]

            desc = meta.get("description") or meta.get("embed_text") or ""
            desc = desc.split(".")[0][:200]  # show first sentence

            def extract_strings(items):
                if not items:
                    return []
                if isinstance(items, list):
                    return [
                        item.get("name", str(item)) if isinstance(item, dict)
                        else str(item)
                        for item in items
                    ]
                return [str(items)]

            formatted_candidates.append({
                "url": c["url"],
                "name": meta.get("name"),
                "desc": desc,
                "duration_min": meta.get("duration_min"),
                "duration_max": meta.get("duration_max"),
                "job_levels": meta.get("job_levels"),
                "languages": extract_strings(meta.get("languages")),
                "test_types": extract_strings(meta.get("test_types")),
                "tags": extract_strings(meta.get("tags")),
            })

        return {
            "original_query": query,
            "rewritten_query": rewritten_query,
            "candidates": formatted_candidates,
            "parsed_info": parsed
        }

    except Exception as e:
        print(f"Error in retrieve_assessments: {e}")
        raise
