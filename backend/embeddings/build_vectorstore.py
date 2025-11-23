# backend/embeddings/build_vectorstore.py
import json
import numpy as np
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = Path(__file__).resolve().parents[1]
EMB_PATH = BASE_DIR / "data" / "embeddings.npy"
META_PATH = BASE_DIR / "data" / "meta.json"
CHROMA_PATH = BASE_DIR / "vector_store"

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

def safe_str(x):
    if x is None:
        return ""
    if isinstance(x, list):
        return ", ".join(str(i) for i in x)
    return str(x)

def safe_int(x):
    if x is None:
        return -1
    try:
        return int(x)
    except:
        return -1

def safe_bool(x):
    if x is None:
        return False
    return bool(x)

def build_vectorstore():
    print("Loading embeddings and metadata...")
    embeddings = np.load(EMB_PATH)
    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("Initializing ChromaDB persistent client at:", CHROMA_PATH)
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)

    # delete old collection if exists
    try:
        chroma_client.delete_collection(name="shl_catalog")
    except:
        pass

    collection = chroma_client.get_or_create_collection(
        name="shl_catalog",
        embedding_function=embed_fn
    )

    print("Preparing flattened metadata...")
    ids = [m["id"] for m in meta]
    docs = [safe_str(m.get("name")) for m in meta]

    cleaned_meta = []
    for m in meta:
        cleaned_meta.append({
            "id": safe_str(m.get("id")),
            "name": safe_str(m.get("name")),
            "url": safe_str(m.get("url")),
            "description": safe_str(m.get("description")),
            "tags": safe_str(m.get("tags")),
            "test_types": safe_str(
                "; ".join(f"{t.get('code')}:{t.get('name')}" for t in m.get("test_types", []))
                if isinstance(m.get("test_types"), list) else safe_str(m.get("test_types"))
            ),
            "test_type_codes": safe_str(m.get("test_type_codes")),
            "job_levels": safe_str(m.get("job_levels")),
            "languages": safe_str(m.get("languages")),
            "duration_min": safe_int(m.get("duration_min")),
            "duration_max": safe_int(m.get("duration_max")),
            "remote_support": safe_bool(m.get("remote_support")),
            "adaptive_support": safe_bool(m.get("adaptive_support")),
        })

    print("Adding documents to vector store...")
    collection.add(
        ids=ids,
        documents=docs,
        metadatas=cleaned_meta,
        embeddings=list(embeddings)
    )

    print("Success! Vector store created at:", CHROMA_PATH)


if __name__ == "__main__":
    build_vectorstore()
