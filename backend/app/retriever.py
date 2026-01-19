from embeddings.hybrid_retriever import HybridRetriever
from llm.query_rewriter import llm_rewrite
from app.key_manager import get_key_manager, rate_limit_sleep

# ---------------------------------------------------------
# Singleton retriever instance
# ---------------------------------------------------------
_retriever = None

def get_retriever():
    """
    Singleton accessor for HybridRetriever.
    Init is now lightweight (API client + NPY load), so we don't need
    complex background loading logic anymore.
    """
    global _retriever
    if _retriever is None:
        print("⚡ Initializing HybridRetriever (Google GenAI)...")
        _retriever = HybridRetriever()
    return _retriever


# ---------------------------------------------------------
# Main public function
# ---------------------------------------------------------
def retrieve_assessments(query: str, top_k: int = 40):
    """
    Full retrieval pipeline:
    1. LLM-based query rewrite (with key rotation)
    2. Hybrid retrieval using vector + lexical + boosting (with key rotation)
    """
    try:
        key_manager = get_key_manager()
        
        # Step 1 — Rewrite using LLM (with key rotation)
        client = key_manager.get_client_and_rotate()
        parsed = llm_rewrite(query, fallback=True, client=client)
        rewritten_query = parsed["rewrite"]
        rate_limit_sleep(1)  # Short sleep between calls
        
        # Step 2 — Retrieve from hybrid retriever (with key rotation)
        retriever = get_retriever()
        client = key_manager.get_client_and_rotate()
        candidates = retriever.retrieve(rewritten_query, top_k=top_k, client=client)
        rate_limit_sleep(1)  # Short sleep for embedding calls

        # Step 3 — Prepare candidates for reranker
        formatted_candidates = []
        for c in candidates:
            meta = c["meta"]

            # Fix description handling
            full_desc = meta.get("description") or meta.get("embed_text") or ""
            
            # Create short description for LLM context
            if full_desc.startswith("."):
                short_desc = full_desc[:200]
            else:
                short_desc = full_desc.split(".")[0][:200]
                if not short_desc: # Fallback if split results in empty
                    short_desc = full_desc[:200]

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
                "desc": short_desc,      # For LLM (short context)
                "description": full_desc, # For UI (full text)
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
