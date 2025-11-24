import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from embeddings.hybrid_retriever import HybridRetriever
from llm.query_rewriter import llm_rewrite

# Initialize retriever once at module load
retriever = HybridRetriever()

def retrieve_assessments(query: str, top_k: int = 40):
    """
    Retrieves assessments using the hybrid retrieval system.
    
    Args:
        query: User's search query
        top_k: Number of results to retrieve (default 40 for reranking)
    
    Returns:
        List of candidate assessments
    """
    try:
        # Step 1: Rewrite query using LLM
        parsed = llm_rewrite(query, fallback=True)
        rewritten_query = parsed["rewrite"]
        
        # Step 2: Retrieve candidates using hybrid retrieval
        candidates = retriever.retrieve(rewritten_query, top_k=top_k)
        
        # Format candidates for reranker
        formatted_candidates = []
        for c in candidates:
            meta = c["meta"]
            
            desc = meta.get("description") or meta.get("embed_text") or ""
            desc = desc.split(".")[0][:200]  # Truncate for API response
            
            # Helper function to extract strings from potential dict lists
            def extract_strings(items):
                if not items:
                    return []
                if isinstance(items, list):
                    return [item.get("name", str(item)) if isinstance(item, dict) else str(item) for item in items]
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
