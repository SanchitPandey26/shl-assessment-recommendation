import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from llm.llm_reranker import llm_rerank

def rerank_results(query: str, retrieval_results: dict, top_k: int = 10):
    """
    Reranks retrieved assessments using LLM.
    
    Args:
        query: Original user query
        retrieval_results: Results from retrieve_assessments()
        top_k: Number of final results to return (default 10)
    
    Returns:
        List of top_k reranked assessments with scores and reasons
    """
    try:
        candidates = retrieval_results["candidates"]
        rewritten_query = retrieval_results["rewritten_query"]
        
        # Call LLM reranker
        reranked = llm_rerank(
            query=query,
            rewritten=rewritten_query,
            candidates=candidates
        )
        
        # Take top_k results
        top_results = reranked[:top_k]
        
        # Enrich with full metadata
        enriched_results = []
        for item in top_results:
            # Find corresponding candidate
            candidate = next((c for c in candidates if c["url"] == item["url"]), None)
            if candidate:
                # Merge candidate data with reranking scores
                enriched_results.append({
                    **candidate,
                    "relevance_score": item["score"],
                    "relevance_reason": item["reason"],
                    "meta": candidate  # Include full metadata for response formatting
                })
        
        return enriched_results
    
    except Exception as e:
        print(f"Error in rerank_results: {e}")
        # Fallback: return first top_k candidates without reranking
        return retrieval_results["candidates"][:top_k]
