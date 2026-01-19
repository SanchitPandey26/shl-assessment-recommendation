from llm.llm_reranker import llm_rerank
from app.key_manager import get_key_manager, rate_limit_sleep

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
        
        key_manager = get_key_manager()

        # Step 1 — use LLM reranker (with key rotation)
        client = key_manager.get_client_and_rotate()
        reranked = llm_rerank(
            query=query,
            rewritten=rewritten_query,
            candidates=candidates,
            client=client
        )
        rate_limit_sleep(1)  # Short sleep after reranking

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
