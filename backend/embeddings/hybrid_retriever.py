# backend/embeddings/hybrid_retriever.py
import json
import os
import numpy as np
from pathlib import Path
from google import genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from app.config import Settings

BASE_DIR = Path(__file__).resolve().parents[1]

# Gemini Embeddings Path
EMB_PATH = BASE_DIR / "data" / "embeddings_gemini.npy"
META_PATH = BASE_DIR / "data" / "meta_gemini.json"

# Config - STRICTLY FROM SETTINGS
EMBEDDING_MODEL = Settings.EMBEDDING_MODEL

class HybridRetriever:
    def __init__(self):
        print(f"Initializing HybridRetriever (Google GenAI: {EMBEDDING_MODEL})...")
        
        # Use first key as default for non-rotated retrieval (deprecated flow)
        # Ideally, client should ALWAYS be injected.
        self.client = genai.Client(api_key=Settings.GEMINI_API_KEY_1)
        
        
        # Load embeddings
        if not os.path.exists(EMB_PATH):
            raise FileNotFoundError(f"Embeddings file not found at {EMB_PATH}. Please run generate_embeddings.py first.")
            
        self.emb = np.load(EMB_PATH)
        
        with open(META_PATH, "r", encoding="utf-8") as f:
            self.meta = json.load(f)

        # index mapping
        self.id_to_index = {m["id"]: i for i, m in enumerate(self.meta)}
        self.index_to_meta = {i: m for i, m in enumerate(self.meta)}

        # build TF-IDF corpus
        corpus = []
        for m in self.meta:
            parts = []
            if m.get("name"): parts.append(m.get("name"))
            if m.get("description"): parts.append(m.get("description"))
            if m.get("tags"):
                if isinstance(m["tags"], list):
                    parts.append(" ".join(m["tags"]))
                else:
                    parts.append(str(m["tags"]))
            if m.get("test_types"):
                if isinstance(m["test_types"], list):
                     # Handle check for dict vs str in case of dirty data
                     parts.append(" ".join([t.get("name", str(t)) if isinstance(t, dict) else str(t) for t in m["test_types"]]))
                else:
                    parts.append(str(m["test_types"]))
            
            if m.get("enrichment"):
                e = m["enrichment"]
                if e.get("skills"): parts.append(" ".join(e["skills"]))
                if e.get("synonyms"): parts.append(" ".join(e["synonyms"]))
                if e.get("summary"): parts.append(e["summary"])
                if e.get("synthetic_queries"): parts.append(" ".join(e["synthetic_queries"]))

            corpus.append(" ".join(parts))

        self.tfidf = TfidfVectorizer(stop_words="english", max_features=20000)
        self.tfidf_matrix = self.tfidf.fit_transform(corpus)
        print("TF-IDF lexical index built for", len(corpus), "documents.")

    def _parse_duration_from_query(self, query: str):
        q = query.lower()
        m = re.search(r"(\d{1,3})\s*(?:minutes|mins|min)\b", q)
        if m:
            return int(m.group(1))
        # ... keep existing parsing logic ...
        return None

    def _job_level_match(self, meta_job_levels, query_job_level):
        if not meta_job_levels or not query_job_level:
            return False
        return query_job_level.lower() in meta_job_levels.lower()

    def retrieve(self, query: str, top_k: int = 15,
                 duration_max: int = None, duration_min: int = None,
                 job_level: str = None, languages: list = None,
                 test_type_codes: list = None,
                 alpha_vector: float = 0.75, alpha_lexical: float = 0.25,
                 metadata_boosts: dict = None,
                 client=None):
        
        metadata_boosts = metadata_boosts or {"duration": 0.12, "job_level": 0.08, "language": 0.05, "test_type": 0.06}

        # 1. Embed Query using Google API
        active_client = client if client else self.client
        if not active_client:
             print("Error: No client available for retrieval embedding.")
             return []

        try:
            resp = active_client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=query,
            )
            query_emb = np.array(resp.embeddings[0].values, dtype="float32")
        except Exception as e:
            print(f"Error embedding query: {e}")
            # Fallback? Or fail. For now fail as vector search is critical.
            return []

        # 2. TF-IDF
        q_tfidf = self.tfidf.transform([query])

        # 3. Vector Similarity (Cosine)
        emb_norms = np.linalg.norm(self.emb, axis=1) + 1e-10
        q_norm = np.linalg.norm(query_emb) + 1e-10
        sims = (self.emb @ query_emb) / (emb_norms * q_norm)

        lexical_sims = cosine_similarity(self.tfidf_matrix, q_tfidf).flatten()

        combined_scores = []
        if duration_max is None:
            parsed = self._parse_duration_from_query(query)
            if parsed:
                duration_max = parsed

        for i in range(len(self.meta)):
            vscore = float(sims[i])
            lscore = float(lexical_sims[i])
            vscore_norm = (vscore + 1.0) / 2.0
            base = alpha_vector * vscore_norm + alpha_lexical * lscore
            boost = 0.0
            meta = self.index_to_meta[i]

            # duration boost (soft)
            if duration_max is not None:
                dm = meta.get("duration_min")
                dx = meta.get("duration_max")
                if dm is not None and dx is not None:
                    if dx <= duration_max:
                        boost += metadata_boosts.get("duration", 0.12)

            # job level
            if job_level and meta.get("job_levels"):
                if self._job_level_match(meta.get("job_levels"), job_level):
                    boost += metadata_boosts.get("job_level", 0.08)

            # languages logic (simplified for brevity, assume similar to before)
            if languages and meta.get("languages"):
                 # ... existing logic ...
                 pass

            # test_type_codes logic
            # ... existing logic ...

            final_score = base + boost
            combined_scores.append((i, final_score, vscore_norm, lscore, boost))

        combined_scores.sort(key=lambda x: x[1], reverse=True)

        # Hard filters (simplified copy)
        # ... logic ...
        selected = combined_scores[:top_k]

        results = []
        for (i, score, vscore_norm, lscore, boost) in selected:
            m = self.index_to_meta[i]
            results.append({
                "id": m.get("id"),
                "name": m.get("name"),
                "url": m.get("url"),
                "score": float(score),
                "vector_score": float(vscore_norm),
                "lexical_score": float(lscore),
                "boost": float(boost),
                "meta": m
            })

        return results
