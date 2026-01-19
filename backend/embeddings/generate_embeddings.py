# backend/embeddings/generate_embeddings.py
import json
import os
import time
import numpy as np
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_PATH = BASE_DIR / "data" / "shl_catalog_clean.json"

# Output paths
EMB_PATH = BASE_DIR / "data" / "embeddings_gemini.npy"
META_PATH = BASE_DIR / "data" / "meta_gemini.json"

# Config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "models/gemini-embedding-001")

def load_clean_data():
    with open(CLEAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_embed_text(item):
    if item.get("embed_text"):
        return item["embed_text"]
    parts = []
    if item.get("name"): parts.append(item["name"])
    if item.get("description"): parts.append(item["description"])
    if item.get("job_levels"): parts.append("Job levels: " + item["job_levels"])
    # Helper to handle list or string
    def clean_str(val):
        if isinstance(val, list):
            return " ".join(val)
        return str(val)

    if item.get("languages"): parts.append("Languages: " + clean_str(item["languages"]))
    if item.get("test_type_expanded"): 
        names = [t["name"] for t in item["test_type_expanded"]]
        parts.append("Test types: " + " ".join(names))
    if item.get("tags"): parts.append("Tags: " + clean_str(item["tags"]))
    if item.get("duration_min"): parts.append(f"duration_min {item.get('duration_min')}")
    
    return " \n ".join(parts)

def generate_embeddings():
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found in .env")
        return

    print("Loading clean data...")
    data = load_clean_data()
    
    print(f"Initializing Google GenAI Client with model: {EMBEDDING_MODEL}")
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Prepare texts
    texts = []
    for item in data:
        item["embed_text"] = ensure_embed_text(item)
        texts.append(item["embed_text"])

    print(f"Generating embeddings for {len(texts)} records...")
    
    all_embeddings = []
    all_embeddings = []
    BATCH_SIZE = 90  # User specified: 90 per request
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        print(f"Processing batch {i} to {i + len(batch)}...")
        
        retries = 3
        for attempt in range(retries):
            try:
                # Batch embedding call
                response = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                )
                # embeddings are in response.embeddings[].values
                batch_embs = [e.values for e in response.embeddings]
                all_embeddings.extend(batch_embs)
                
                print("Batch done. Sleeping for 60s to respect rate limits...")
                time.sleep(60) 
                break # Success, move to next batch
            except Exception as e:
                print(f"Error in batch {i} (Attempt {attempt+1}/{retries}): {e}")
                if "429" in str(e):
                    print("Hit Rate Limit. Sleeping for 60s...")
                    time.sleep(60)
                else:
                    time.sleep(10)
        else:
             print(f"Failed batch {i} after {retries} attempts.")
             break

    if len(all_embeddings) != len(texts):
        print(f"Warning: Count mismatch. Generated {len(all_embeddings)}, expected {len(texts)}")
        return

    # Convert to numpy
    emb_array = np.array(all_embeddings, dtype="float32")
    
    print("Saving embeddings to:", EMB_PATH)
    np.save(EMB_PATH, emb_array)

    # Save metadata
    print("Saving metadata to:", META_PATH)
    meta = []
    for item in data:
        meta.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "url": item.get("url"),
            "description": item.get("description"),
            "tags": item.get("tags"),
            "test_types": item.get("test_type_expanded"),
            "test_type_codes": item.get("test_type_codes"),
            "job_levels": item.get("job_levels"),
            "languages": item.get("languages"),
            "duration_min": item.get("duration_min"),
            "duration_max": item.get("duration_max"),
            "remote_support": item.get("remote_support"),
            "adaptive_support": item.get("adaptive_support"),
            "embed_text": item.get("embed_text"),
            "enrichment": item.get("enrichment"),
        })

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("Done! Migration to Google Embeddings complete.")

if __name__ == "__main__":
    generate_embeddings()
