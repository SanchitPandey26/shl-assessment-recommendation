# backend/test_llm_pipeline.py
import json
from llm.query_rewriter import llm_rewrite
from llm.llm_reranker import llm_rerank
from embeddings.hybrid_retriever import HybridRetriever
from dotenv import load_dotenv
load_dotenv()


def run_test():
    query = "Hiring a Java developer who collaborates well. Test around 40 minutes."

    print("\n--- Original Query ---")
    print(query)

    parsed = llm_rewrite(query)

    print("\n--- Rewrite ---")
    print(json.dumps(parsed, indent=2))

    retriever = HybridRetriever()
    candidates = retriever.retrieve(query, top_k=40)

    # -------- UPDATED: full metadata for reranker --------
    formatted = []

    for c in candidates:
        meta = c["meta"]

        desc = meta.get("description", "")
        if desc:
            desc = desc.replace("\n", " ")[:200]

        formatted.append({
            "url": meta.get("url"),
            "name": meta.get("name"),
            "desc": desc,
            "duration_min": meta.get("duration_min"),
            "duration_max": meta.get("duration_max"),
            "job_levels": meta.get("job_levels"),
            "languages": meta.get("languages"),
            "test_types": meta.get("test_types"),
            "tags": meta.get("tags"),
        })

    print("\nRetrieving...\n")

    reranked = llm_rerank(
        query=query,
        rewritten=parsed["rewrite"],
        candidates=formatted
    )

    print("\n--- Top 5 Reranked ---")
    for r in reranked[:5]:
        print(f"{r['score']:.3f} | {r['url']}  — {r['reason']}")


if __name__ == "__main__":
    run_test()
