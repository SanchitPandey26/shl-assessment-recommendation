import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_PATH = BASE_DIR / "vector_store"

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

model = SentenceTransformer(MODEL_NAME)

client = chromadb.PersistentClient(path=str(CHROMA_PATH))

collection = client.get_collection(name="shl_catalog")

def retrieve(query: str, top_k: int = 15):
    query_emb = model.encode([query])[0]

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k
    )

    ids = results["ids"][0]
    metas = results["metadatas"][0]

    return [
        {
            "id": id_,
            "name": meta["name"],
            "url": meta["url"],
            "tags": meta["tags"],
            "test_types": meta["test_types"],
            "remote": meta["remote"],
            "adaptive": meta["adaptive"],
            "score": results["distances"][0][i]
        }
        for i, (id_, meta) in enumerate(zip(ids, metas))
    ]
