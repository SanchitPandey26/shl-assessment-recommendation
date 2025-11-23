# backend/embeddings/hybrid_retriever.py
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

BASE_DIR = Path(__file__).resolve().parents[1]

# BGE small model paths
EMB_PATH = BASE_DIR / "data" / "embeddings_bge_small.npy"
META_PATH = BASE_DIR / "data" / "meta_bge_small.json"

#BGE Base model paths
# EMB_PATH = BASE_DIR / "data" / "embeddings_bge_base.npy"
# META_PATH = BASE_DIR / "data" / "meta_bge_base.json"

# Small BGE model
MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Base BGE model
# MODEL_NAME = "BAAI/bge-base-en-v1.5"

class HybridRetriever:
    def __init__(self, model_name=MODEL_NAME):
        print("Initializing HybridRetriever (BGE-small)...")
        # print("Initializing HybridRetriever (BGE-base)...")
        self.model = SentenceTransformer(model_name)
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
            if m.get("name"):
                parts.append(m.get("name"))
            if m.get("description"):
                parts.append(m.get("description"))
            if m.get("tags"):
                if isinstance(m["tags"], list):
                    parts.append(" ".join(m["tags"]))
                else:
                    parts.append(str(m["tags"]))
            if m.get("test_types"):
                if isinstance(m["test_types"], list):
                    parts.append(" ".join([t["name"] for t in m["test_types"]]))
                else:
                    parts.append(str(m["test_types"]))
            corpus.append(" ".join(parts))

        self.tfidf = TfidfVectorizer(stop_words="english", max_features=20000)
        self.tfidf_matrix = self.tfidf.fit_transform(corpus)
        print("TF-IDF lexical index built for", len(corpus), "documents.")

    def _parse_duration_from_query(self, query: str):
        q = query.lower()
        m = re.search(r"(\d{1,3})\s*(?:minutes|mins|min)\b", q)
        if m:
            return int(m.group(1))
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours|hour)\b", q)
        if m2:
            hours = float(m2.group(1))
            return int(round(hours * 60))
        m3 = re.search(r"(?:under|less than|no more than|<=)\s*(\d{1,3})\s*(?:minutes|mins|min)\b", q)
        if m3:
            return int(m3.group(1))
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
                 metadata_boosts: dict = None):
        metadata_boosts = metadata_boosts or {"duration": 0.12, "job_level": 0.08, "language": 0.05, "test_type": 0.06}

        query_emb = self.model.encode([query])[0]
        q_tfidf = self.tfidf.transform([query])

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

            # languages
            if languages and meta.get("languages"):
                meta_langs = meta.get("languages")
                if isinstance(meta_langs, list):
                    meta_langs_lc = [l.lower() for l in meta_langs]
                    for lg in languages:
                        if lg.lower() in " ".join(meta_langs_lc):
                            boost += metadata_boosts.get("language", 0.05)
                            break
                else:
                    for lg in languages:
                        if lg.lower() in str(meta_langs).lower():
                            boost += metadata_boosts.get("language", 0.05)
                            break

            # test_type_codes
            if test_type_codes and meta.get("test_type_codes"):
                meta_codes = [str(c).strip().upper() for c in (meta.get("test_type_codes") or [])]
                for tc in test_type_codes:
                    if str(tc).strip().upper() in meta_codes:
                        boost += metadata_boosts.get("test_type", 0.06)
                        break

            final_score = base + boost
            combined_scores.append((i, final_score, vscore_norm, lscore, boost))

        combined_scores.sort(key=lambda x: x[1], reverse=True)

        # hard filters if explicitly passed
        hard_filtered = []
        for (i, score, vscore_norm, lscore, boost) in combined_scores:
            meta = self.index_to_meta[i]
            ok = True
            if duration_min is not None or duration_max is not None:
                dm = meta.get("duration_min")
                dx = meta.get("duration_max")
                if dm is not None and dx is not None:
                    if duration_max is not None and dx > duration_max:
                        ok = False
                    if duration_min is not None and dm < duration_min:
                        ok = False
            if ok:
                hard_filtered.append((i, score, vscore_norm, lscore, boost))

        if len(hard_filtered) == 0:
            selected = combined_scores[:top_k]
        else:
            selected = hard_filtered[:top_k]

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

    def rerank_with_llm(self, query: str, candidates: list, llm_client=None, model="gpt-4o-mini", prompt_template=None):
        if llm_client is None:
            return candidates
        return candidates
