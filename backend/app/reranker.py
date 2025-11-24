import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from llm.llm_reranker import llm_rerank

# ---------------------------------------------------------
# Lazy loading reranker (lightweight but consistent)
# ---------------------------------------------------------
def rerank_results(query: str, retrieval_results: dict, top_k: int = 10):
    """
    Reranks retrieved assessments using the LLM-based reranker.

    Args:
        query: original user query
        retrieval_results: output of retrieve_assessments()
        top_k: number of final results to return

    Returns:
        list of enriched candidate dicts
    """
    try:
        candidates = retrieval_results["candidates"]
        rewritten_query = retrieval_results["rewritten_query"]

        # Step 1 — use LLM reranker
        reranked = llm_rerank(
            query=query,
            rewritten=rewritten_query,
            candidates=candidates
        )

        top_results = reranked[:top_k]

        # Step 2 — enrich with metadata
        enriched_results = []
        for item in top_results:
            candidate = next(
                (c for c in candidates if c["url"] == item["url"]),
                None
            )
            if candidate:
                enriched_results.append({
                    **candidate,  # full metadata
                    "relevance_score": item["score"],
                    "relevance_reason": item["reason"],
                    "meta": candidate
                })

        return enriched_results

    except Exception as e:
        print(f"Error in rerank_results: {e}")
        return retrieval_results["candidates"][:top_k]
