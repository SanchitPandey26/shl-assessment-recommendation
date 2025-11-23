import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_PATH = BASE_DIR / "data" / "shl_catalog_clean.json"
EMB_PATH = BASE_DIR / "data" / "embeddings.npy"
META_PATH = BASE_DIR / "data" / "meta.json"

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

def load_clean_data():
    with open(CLEAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_embed_text(item):
    """If embed_text exists keep it; otherwise build a richer embed_text using available fields."""
    if item.get("embed_text"):
        return item["embed_text"]
    parts = []
    if item.get("name"):
        parts.append(item["name"])
    if item.get("description"):
        parts.append(item["description"])
    if item.get("job_levels"):
        parts.append("Job levels: " + item["job_levels"])
    if item.get("languages"):
        if isinstance(item["languages"], list):
            parts.append("Languages: " + " ".join(item["languages"]))
        else:
            parts.append("Languages: " + str(item["languages"]))
    # include test type names (expand)
    if item.get("test_type_expanded"):
        parts.append("Test types: " + " ".join([t["name"] for t in item["test_type_expanded"]]))
    # include tags
    if item.get("tags"):
        if isinstance(item["tags"], list):
            parts.append("Tags: " + " ".join(item["tags"]))
        else:
            parts.append("Tags: " + str(item["tags"]))
    # duration signals
    if item.get("duration_min"):
        parts.append(f"duration_min {item.get('duration_min')}")
    return " \n ".join(parts)

def generate_embeddings():
    print("Loading clean data...")
    data = load_clean_data()

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    # ensure embed_text and create canonical meta
    for item in data:
        item["embed_text"] = ensure_embed_text(item)

    texts = [item["embed_text"] for item in data]
    ids = [item["id"] for item in data]

    print(f"Generating embeddings for {len(texts)} records...")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=16
    )

    print("Saving embeddings to:", EMB_PATH)
    np.save(EMB_PATH, embeddings)

    # Save rich metadata (used by hybrid retriever). This file keeps structured fields.
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
            # keep embed_text too for lexical index
            "embed_text": item.get("embed_text")
        })

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("Done! Embeddings and meta saved.")
    print("Files:")
    print(" -", EMB_PATH)
    print(" -", META_PATH)

if __name__ == "__main__":
    generate_embeddings()
