import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import hashlib
import time
import sys

# -----------------------------------------------------------
# Paths
# -----------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

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

import os
import random
from google import genai
from dotenv import load_dotenv

load_dotenv()

# -----------------------------------------------------------
# KEY MANAGER
# -----------------------------------------------------------
class KeyManager:
    def __init__(self):
        # Load keys from GEMINI_API_KEY_1, _2, _3 (no fallback to unsuffixed)
        self.keys = []
        
        for i in range(1, 4):
            k = os.environ.get(f"GEMINI_API_KEY_{i}")
            if k:
                self.keys.append(k)
        
        if not self.keys:
            raise ValueError("ERROR: No GEMINI_API_KEY_1/2/3 found in environment! Set at least one.")
            
        print(f"Loaded {len(self.keys)} API keys for rotation.")
        self.clients = [genai.Client(api_key=k) for k in self.keys]
        self.current_idx = 0
        self.call_count = 0  # Track calls for proactive rotation

    def get_client(self):
        return self.clients[self.current_idx]

    def rotate(self):
        old_idx = self.current_idx
        self.current_idx = (self.current_idx + 1) % len(self.clients)
        print(f"🔄 Rotating key (Index {old_idx} -> {self.current_idx})")
        return self.get_client()
    
    def get_client_and_rotate(self):
        """Get current client and PROACTIVELY rotate to next key for next call.
        This distributes load across all keys evenly."""
        client = self.get_client()
        self.call_count += 1
        self.rotate()  # Proactive rotation after each call
        return client

# -----------------------------------------------------------
# Main Evaluation with Rotation
# -----------------------------------------------------------

def run_evaluation():
    print("Loading Excel train/test dataset...")
    df = pd.read_excel(EXCEL_PATH)

    query_col = "Query"
    url_cols = [c for c in df.columns if c != query_col]

    retriever = HybridRetriever()
    key_manager = KeyManager()

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
        
        # ------------------------------------------------------------
        # STEP 1: LLM REWRITE (Gemini) - WITH RETRY / ROTATION
        # ------------------------------------------------------------
        rewritten_query = query
        parsed = {"rewrite": query}
        
        max_retries = len(key_manager.keys) * 2
        for attempt in range(max_retries):
            client = key_manager.get_client_and_rotate()  # Proactive rotation
            try:
                parsed = llm_rewrite(query, fallback=True, client=client)
                rewritten_query = parsed["rewrite"]
                
                # With 3 keys at 5 RPM each = 15 RPM total = 4s between calls
                # Adding small buffer for safety
                print(f"Rewrite success (Key {key_manager.current_idx}). Sleeping 5s...")
                time.sleep(5) 
                break
                
            except Exception as e:
                print(f"Rewrite failed with Key {key_manager.current_idx}: {e}")
                if "429" in str(e) or "quota" in str(e).lower():
                    print("Hit Rate Limit (429). Sleeping 60s and rotating...")
                    time.sleep(60)
                    key_manager.rotate()
                else:
                    # Non-rate limit error? maybe fallback immediately
                    print("Non-429 error, sticking to query.")
                    break
        
        
        print("\nRewritten Query:")
        print(rewritten_query)


        # ------------------------------------------------------------
        # STEP 2: HYBRID RETRIEVAL
        # ------------------------------------------------------------
        # Use the same client (or rotated) for retrieval embedding
        # We should use retry/rotate logic here too strictly speaking, 
        # but retrieval embedding is cheaper/less likely to 429 than generation usually.
        # However, to be safe, let's wrap it or just use the current valid client.
        
        candidates = []
        for attempt in range(max_retries):
             client = key_manager.get_client_and_rotate()  # Proactive rotation
             try:
                 candidates = retriever.retrieve(rewritten_query, top_k=40, client=client)
                 if not candidates:
                     print("Warning: Retrieved 0 candidates.")
                 
                 # Embedding calls are lighter, shorter sleep
                 time.sleep(2) 
                 break
             except Exception as e:
                 print(f"Retrieval embedding failed with Key {key_manager.current_idx}: {e}")
                 if "429" in str(e) or "quota" in str(e).lower():
                    print("Hit Rate Limit (429) in retrieval. Sleeping 60s and rotating...")
                    time.sleep(60)
                    key_manager.rotate()
                 else:
                    break

        formatted_candidates = []
        for c in candidates:
            meta = c["meta"]
            desc = meta.get("description") or meta.get("embed_text") or ""
            desc = desc.split(".")[0][:200]

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
        # STEP 3: LLM RERANKING - WITH RETRY / ROTATION
        # ------------------------------------------------------------
        ck = cache_key(query, formatted_candidates)

        if ck in LLM_CACHE:
            print("Using cached rerank output.")
            reranked = LLM_CACHE[ck]
        else:
            print("Calling LLM reranker...")
            reranked = None
            
            for attempt in range(max_retries):
                client = key_manager.get_client_and_rotate()  # Proactive rotation
                try:
                    reranked = llm_rerank(
                        query=query,
                        rewritten=rewritten_query,
                        candidates=formatted_candidates,
                        client=client
                    )
                    
                    print(f"Rerank success (Key {key_manager.current_idx}). Sleeping 5s...")
                    time.sleep(5)
                    break
                    
                except Exception as e:
                    print(f"Rerank failed with Key {key_manager.current_idx}: {e}")
                    if "429" in str(e) or "quota" in str(e).lower():
                        print("Hit Rate Limit (429). Sleeping 60s and rotating...")
                        time.sleep(60)
                        key_manager.rotate()
                    else:
                         break # Non-retriable error

            if reranked is None:
                 print("⚠ Reranker failed all attempts, falling back to hybrid order.")
                 reranked = [
                    {"url": c["url"], "score": 1 - 0.05 * i, "reason": "fallback"}
                    for i, c in enumerate(formatted_candidates[:10])
                ]

            LLM_CACHE[ck] = reranked
            save_cache()


        # Take top 10 *after reranking*
        final_urls = [normalize_url(x["url"]) for x in reranked[:10]]
        
        # ------------------------------------------------------------
        # STEP 4: Recall@10
        # ------------------------------------------------------------
        recall10 = compute_recall_at_10(gt_urls, final_urls)
        recall_scores.append(recall10)

        print("Recall@10 =", recall10)
        print(f"Completed {idx+1}/{len(df)} queries.")

        # Store full results immediately (safety)
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
    if not recall_scores:
        print("No results generated.")
        return

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
