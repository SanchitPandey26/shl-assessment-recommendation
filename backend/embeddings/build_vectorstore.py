# backend/embeddings/build_vectorstore.py
import json
import numpy as np
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

BASE_DIR = Path(__file__).resolve().parents[1]
EMB_PATH = BASE_DIR / "data" / "embeddings_bge_base.npy"
META_PATH = BASE_DIR / "data" / "meta_bge_base.json"
CHROMA_PATH = BASE_DIR / "vector_store_bge_base"

MODEL_NAME = "BAAI/bge-base-en-v1.5"


def sanitize(value):
    """Chroma-safe conversion of metadata values."""
    if value is None:
        return ""      # safest default for strings
    if isinstance(value, list):
        return ", ".join([str(v) for v in value])
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


def build_vectorstore():
    print("Loading embeddings and metadata...")
    embeddings = np.load(EMB_PATH)

    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("Initializing ChromaDB persistent client at:", CHROMA_PATH)
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODEL_NAME
    )

    try:
        chroma_client.delete_collection("shl_catalog_bge_small")
    except:
        pass

    collection = chroma_client.get_or_create_collection(
        name="shl_catalog_bge_small",
        embedding_function=embed_fn
    )

    print("Preparing metadata...")

    ids = []
    docs = []
    cleaned_meta = []

    for m in meta:
        ids.append(sanitize(m.get("id")))
        docs.append(sanitize(m.get("name")))

        cleaned_meta.append({
            "id": sanitize(m.get("id")),
            "name": sanitize(m.get("name")),
            "url": sanitize(m.get("url")),
            "description": sanitize(m.get("description")),
            "tags": sanitize(m.get("tags")),
            "test_types": sanitize(m.get("test_types")),
            "test_type_codes": sanitize(m.get("test_type_codes")),
            "job_levels": sanitize(m.get("job_levels")),
            "languages": sanitize(m.get("languages")),
            "duration_min": int(m["duration_min"]) if m.get("duration_min") is not None else -1,
            "duration_max": int(m["duration_max"]) if m.get("duration_max") is not None else -1,
            "remote_support": bool(m.get("remote_support")),
            "adaptive_support": bool(m.get("adaptive_support")),
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
