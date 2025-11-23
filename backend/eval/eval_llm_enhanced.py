import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import hashlib
import time

from embeddings.hybrid_retriever import HybridRetriever
from llm.query_rewriter import llm_rewrite
from llm.llm_reranker import llm_rerank


# -----------------------------------------------------------
# Paths
# -----------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = BASE_DIR / "data" / "train_test" / "Gen_AI Dataset.xlsx"

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUT_JSON = BASE_DIR / "eval" / f"llm_enhanced_results_{timestamp}.json"
OUT_CSV = BASE_DIR / "eval" / f"llm_enhanced_results_{timestamp}.csv"

OUT_JSON.parent.mkdir(exist_ok=True, parents=True)



# -----------------------------------------------------------
# Utilities
# -----------------------------------------------------------

def normalize_url(u: str):
    if not isinstance(u, str):
        return None
    u = u.strip().lower()
    u = u.replace("http://", "https://")
    if u.endswith("/"):
        u = u[:-1]
    return u


def compute_recall_at_10(gt_urls, retrieved_urls):
    gt_set = set(gt_urls)
    ret_set = set(retrieved_urls)

    if len(gt_set) == 0:
        return 0.0

    matches = gt_set.intersection(ret_set)
    return len(matches) / len(gt_set)



# -----------------------------------------------------------
# Simple LLM CACHE (very important for cost control)
# -----------------------------------------------------------

CACHE_FILE = BASE_DIR / "eval" / "llm_cache.json"

try:
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        LLM_CACHE = json.load(f)
except:
    LLM_CACHE = {}

def cache_key(query, candidates):
    h = hashlib.sha1()
    h.update(query.encode("utf-8"))
    h.update(json.dumps(candidates, sort_keys=True).encode("utf-8"))
    return h.hexdigest()

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(LLM_CACHE, f, indent=2)



# -----------------------------------------------------------
# Main Evaluation
# -----------------------------------------------------------

def run_evaluation():
    print("Loading Excel train/test dataset...")
    df = pd.read_excel(EXCEL_PATH)

    query_col = "Query"
    url_cols = [c for c in df.columns if c != query_col]

    retriever = HybridRetriever()

    results = []
    recall_scores = []

    print("\nStarting LLM-enhanced evaluation...\n")

    for idx, row in df.iterrows():
        query = str(row[query_col]).strip()

        # ----- Ground truth URLs -----
        gt_urls = [
            normalize_url(row[c])
            for c in url_cols
            if isinstance(row[c], str) and row[c].strip()
        ]

        print(f"\n==============================")
        print(f"Query {idx+1}: {query}")
        print("Ground truth:", gt_urls)

        # ------------------------------------------------------------
        # STEP 1: LLM REWRITE (Gemini)
        # ------------------------------------------------------------
        try:
            parsed = llm_rewrite(query, fallback=True)
            rewritten_query = parsed["rewrite"]
        except Exception as e:
            print("Rewrite failed, using raw query:", e)
            parsed = {"rewrite": query}
            rewritten_query = query

        print("\nRewritten Query:")
        print(rewritten_query)


        # ------------------------------------------------------------
        # STEP 2: HYBRID RETRIEVAL (20 candidates for reranking)
        # ------------------------------------------------------------
        candidates = retriever.retrieve(rewritten_query, top_k=20)

        formatted_candidates = []
        for c in candidates:
            meta = c["meta"]

            desc = meta.get("description") or meta.get("embed_text") or ""
            desc = desc.split(".")[0][:200]  # tiny, safe truncation

            formatted_candidates.append({
                "url": c["url"],
                "name": meta.get("name"),
                "desc": desc,
                "duration_min": meta.get("duration_min"),
                "duration_max": meta.get("duration_max"),
                "job_levels": meta.get("job_levels"),
                "languages": meta.get("languages"),
                "test_types": meta.get("test_types"),
                "tags": meta.get("tags"),
            })


        # ------------------------------------------------------------
        # STEP 3: LLM RERANKING (Gemini 2.5 Flash)
        # ------------------------------------------------------------
        ck = cache_key(query, formatted_candidates)

        if ck in LLM_CACHE:
            print("Using cached rerank output.")
            reranked = LLM_CACHE[ck]
        else:
            print("Calling LLM reranker...")
            try:
                reranked = llm_rerank(
                    query=query,
                    rewritten=rewritten_query,
                    candidates=formatted_candidates
                )
            except Exception as e:
                print("⚠ Reranker failed, falling back:", e)
                # fallback: hybrid order only
                reranked = [
                    {"url": c["url"], "score": 1 - 0.05 * i, "reason": "fallback"}
                    for i, c in enumerate(formatted_candidates[:10])
                ]

            LLM_CACHE[ck] = reranked
            save_cache()


        # Take top 10 *after reranking*
        final_urls = [normalize_url(x["url"]) for x in reranked[:10]]
        print("\nTop 10 After Reranker:")
        for u in final_urls:
            print(" -", u)


        # ------------------------------------------------------------
        # STEP 4: Recall@10
        # ------------------------------------------------------------
        recall10 = compute_recall_at_10(gt_urls, final_urls)
        recall_scores.append(recall10)

        print("Recall@10 =", recall10)

        # Store full results
        results.append({
            "query": query,
            "rewrite": rewritten_query,
            "ground_truth": gt_urls,
            "retrieved_final": final_urls,
            "recall_at_10": recall10,
            "parsed": parsed,
        })


    # ------------------------------------------------------------
    # FINAL METRICS
    # ------------------------------------------------------------
    mean_recall = sum(recall_scores) / len(recall_scores)

    # Save JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "mean_recall_at_10": mean_recall,
            "results": results
        }, f, indent=2)

    # Save CSV summary
    pd.DataFrame({
        "query": [r["query"] for r in results],
        "recall_at_10": recall_scores
    }).to_csv(OUT_CSV, index=False)

    print("\n============================================")
    print("Saved LLM-enhanced evaluation results to:")
    print("  JSON:", OUT_JSON)
    print("  CSV :", OUT_CSV)
    print("Mean Recall@10 =", mean_recall)
    print("============================================")


if __name__ == "__main__":
    run_evaluation()
