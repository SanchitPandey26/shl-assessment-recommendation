import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from embeddings.hybrid_retriever import HybridRetriever

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = BASE_DIR / "data" / "train_test" / "Gen_AI Dataset.xlsx"

# Timestamped output paths
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUT_JSON = BASE_DIR / "eval" / f"baseline_results_{timestamp}.json"
OUT_CSV = BASE_DIR / "eval" / f"baseline_results_{timestamp}.csv"


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
    """Recall@10 = (# correct retrieved) / (total ground truth)."""
    gt_set = set(gt_urls)
    ret_set = set(retrieved_urls)

    if len(gt_set) == 0:
        return 0.0

    matches = gt_set.intersection(ret_set)
    return len(matches) / len(gt_set)


# -----------------------------------------------------------
# Main Evaluation
# -----------------------------------------------------------

def run_evaluation():
    print("Loading Excel train set...")
    df = pd.read_excel(EXCEL_PATH)

    # Expected format:
    # Query | URL1 | URL2 | URL3 ...
    query_col = "Query"
    url_cols = [c for c in df.columns if c != query_col]

    retriever = HybridRetriever()

    results = []
    recall_scores = []

    for idx, row in df.iterrows():
        query = str(row[query_col]).strip()

        # Collect GT URLs
        gt_urls = [
            normalize_url(row[c])
            for c in url_cols
            if isinstance(row[c], str) and row[c].strip()
        ]

        print(f"\n--- Query {idx+1} ---")
        print("Query:", query)
        print("Ground truth URLs:", gt_urls)

        # Retrieve top 10
        retrieved = retriever.retrieve(query, top_k=10)
        retrieved_urls = [normalize_url(item["url"]) for item in retrieved]

        recall10 = compute_recall_at_10(gt_urls, retrieved_urls)
        recall_scores.append(recall10)

        print("Recall@10 =", recall10)

        results.append({
            "query": query,
            "ground_truth": gt_urls,
            "retrieved": retrieved_urls,
            "recall_at_10": recall10
        })

    # Compute mean recall
    mean_recall = sum(recall_scores) / len(recall_scores)

    # Save JSON full results
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "mean_recall_at_10": mean_recall,
            "results": results
        }, f, indent=2)

    # Save summary CSV
    pd.DataFrame({
        "query": [r["query"] for r in results],
        "recall_at_10": recall_scores
    }).to_csv(OUT_CSV, index=False)

    print("\nSaved baseline results to:")
    print("  JSON:", OUT_JSON)
    print("  CSV :", OUT_CSV)
    print("\nFinal Mean Recall@10:", mean_recall)


if __name__ == "__main__":
    run_evaluation()
