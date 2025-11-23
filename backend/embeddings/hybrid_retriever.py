"""
Hybrid retriever that:
 - loads embeddings.npy + meta.json
 - builds a TF-IDF lexical index on (name + description + tags)
 - given a query and optional constraints (duration_max, job_level, languages, test_type_codes),
   returns a fused ranking: alpha_vector * vector_sim + alpha_lexical * lexical_sim + metadata_boosts
 - If pre-filter reduces candidates to zero, automatically falls back to no-filter mode.

Usage:
    from embeddings.hybrid_retriever import HybridRetriever
    r = HybridRetriever()
    results = r.retrieve("java developer, 40 minutes", top_k=10, duration_max=45)
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

BASE_DIR = Path(__file__).resolve().parents[1]
EMB_PATH = BASE_DIR / "data" / "embeddings.npy"
META_PATH = BASE_DIR / "data" / "meta.json"
MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

class HybridRetriever:
    def __init__(self, model_name=MODEL_NAME):
        print("Initializing HybridRetriever...")
        self.model = SentenceTransformer(model_name)
        self.emb = np.load(EMB_PATH)
        with open(META_PATH, "r", encoding="utf-8") as f:
            self.meta = json.load(f)

        # build a mapping id -> index
        self.id_to_index = {m["id"]: i for i, m in enumerate(self.meta)}
        self.index_to_meta = {i: m for i, m in enumerate(self.meta)}

        # build lexical corpus (simple: name + description + tags)
        corpus = []
        for m in self.meta:
            parts = []
            if m.get("name"):
                parts.append(m.get("name"))
            if m.get("description"):
                parts.append(m.get("description"))
            if m.get("tags"):
                # tags may be list or string
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

    # ----------------------
    # small utilities
    # ----------------------
    def _normalize_url(self, u: str):
        if not u:
            return None
        return u.strip().lower().replace("http://", "https://")

    def _parse_duration_from_query(self, query: str):
        """extract explicit duration in minutes from query if present (e.g., '40 minutes' or 'less than 1 hour')."""
        q = query.lower()
        # minutes
        m = re.search(r"(\d{1,3})\s*(?:minutes|mins|min)\b", q)
        if m:
            return int(m.group(1))
        # hours patterns: '1 hour', '1.5 hours'
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours|hour)\b", q)
        if m2:
            hours = float(m2.group(1))
            return int(round(hours * 60))
        # phrases like 'under 90 minutes' or 'no more than 45 mins'
        m3 = re.search(r"(?:under|less than|no more than|<=)\s*(\d{1,3})\s*(?:minutes|mins|min)\b", q)
        if m3:
            return int(m3.group(1))
        return None

    def _job_level_match(self, meta_job_levels, query_job_level):
        """Simple substring match between normalized job levels strings."""
        if not meta_job_levels or not query_job_level:
            return False
        return query_job_level.lower() in meta_job_levels.lower()

    # ----------------------
    # Main retrieve function
    # ----------------------
    def retrieve(self, query: str, top_k: int = 15,
                 duration_max: int = None, duration_min: int = None,
                 job_level: str = None, languages: list = None,
                 test_type_codes: list = None,
                 alpha_vector: float = 0.75, alpha_lexical: float = 0.25,
                 metadata_boosts: dict = None):
        """
        Returns a list of result dicts with fields:
        {id, name, url, score, vector_score, lexical_score, meta}

        metadata_boosts: optional dict to control boosts for matches, e.g.
            {"duration": 0.10, "job_level": 0.05, "language": 0.03, "test_type": 0.05}
        """
        metadata_boosts = metadata_boosts or {"duration": 0.12, "job_level": 0.08, "language": 0.05, "test_type": 0.06}

        # 1) Compute query embedding and lexical vector
        query_emb = self.model.encode([query])[0]
        q_tfidf = self.tfidf.transform([query])

        # 2) Candidate set: consider all documents but we will apply metadata soft-filter/boosts
        # To be efficient, compute vector similarities to all (small catalog ~377).
        emb_norms = np.linalg.norm(self.emb, axis=1) + 1e-10
        q_norm = np.linalg.norm(query_emb) + 1e-10
        sims = (self.emb @ query_emb) / (emb_norms * q_norm)  # cosine similarity

        # 3) Lexical similarities
        lexical_sims = cosine_similarity(self.tfidf_matrix, q_tfidf).flatten()

        # 4) Combine scores and apply metadata boosts (soft)
        combined_scores = []
        candidate_indices = list(range(len(self.meta)))
        for i in candidate_indices:
            vscore = float(sims[i])  # -1..1
            lscore = float(lexical_sims[i])  # 0..1
            # normalize vscore from [-1,1] to [0,1]
            vscore_norm = (vscore + 1.0) / 2.0

            base = alpha_vector * vscore_norm + alpha_lexical * lscore

            # metadata boosts (soft)
            boost = 0.0
            meta = self.index_to_meta[i]

            # duration constraint: prefer items that fit in requested max duration
            if duration_max is None:
                # try parse from query
                parsed = self._parse_duration_from_query(query)
                if parsed:
                    duration_max = parsed

            if duration_max is not None:
                dm = meta.get("duration_min")
                dx = meta.get("duration_max")
                # if meta has durations and it fits within user's max -> boost
                if dm is not None and dx is not None:
                    if dx <= duration_max:
                        boost += metadata_boosts.get("duration", 0.12)
                # if meta has no duration info, we do NOT penalize strongly (so don't subtract)
            # job_level boost
            if job_level and meta.get("job_levels"):
                if self._job_level_match(meta.get("job_levels"), job_level):
                    boost += metadata_boosts.get("job_level", 0.08)
            # language boost
            if languages and meta.get("languages"):
                meta_langs = meta.get("languages")
                if isinstance(meta_langs, list):
                    meta_langs_lc = [l.lower() for l in meta_langs]
                    for lg in languages:
                        if lg.lower() in " ".join(meta_langs_lc):
                            boost += metadata_boosts.get("language", 0.05)
                            break
                else:
                    # meta languages are string
                    for lg in languages:
                        if lg.lower() in str(meta_langs).lower():
                            boost += metadata_boosts.get("language", 0.05)
                            break
            # test type boost (codes)
            if test_type_codes and meta.get("test_type_codes"):
                # compare codes as strings
                meta_codes = [str(c).strip().upper() for c in (meta.get("test_type_codes") or [])]
                for tc in test_type_codes:
                    if str(tc).strip().upper() in meta_codes:
                        boost += metadata_boosts.get("test_type", 0.06)
                        break

            final_score = base + boost
            combined_scores.append((i, final_score, vscore_norm, lscore, boost))

        # 5) Sort by final_score and pick top_k
        combined_scores.sort(key=lambda x: x[1], reverse=True)

        # 6) After sorting, attempt to apply any hard filters (only if explicitly requested)
        # Hard filters: if user passed duration_min/max we remove items that definitely do not match.
        hard_filtered = []
        for (i, score, vscore_norm, lscore, boost) in combined_scores:
            meta = self.index_to_meta[i]
            ok = True
            # hard duration
            if duration_min is not None or duration_max is not None:
                dm = meta.get("duration_min")
                dx = meta.get("duration_max")
                # If meta has duration info and it conflicts with requested window -> drop
                if dm is not None and dx is not None:
                    if duration_max is not None and dx > duration_max:
                        ok = False
                    if duration_min is not None and dm < duration_min:
                        ok = False
            if ok:
                hard_filtered.append((i, score, vscore_norm, lscore, boost))

        if len(hard_filtered) == 0:
            # fallback: if hard filters removed everything, use best combined_scores (no hard filter)
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

    # ----------------------
    # Optional: LLM rerank placeholder (user will add API keys)
    # ----------------------
    def rerank_with_llm(self, query: str, candidates: list, llm_client=None, model="gpt-4o-mini", batch_size=10, prompt_template=None):
        """
        Placeholder which accepts a 'llm_client' instance you provide (e.g., openai or Gemini).
        It should return the same list of candidates but re-ordered by LLM scores.
        We do NOT make any external calls here.

        Example prompt_template:
        "Rate the relevance of the candidate assessment to this query on a scale 0-100 and give one-line reason.\nQuery: {query}\nCandidate: {candidate_text}\nResponse format: JSON {score: int, reason: str}\n"
        """
        # If llm_client is None, just return candidates unchanged
        if llm_client is None:
            return candidates

        # Implement batching and calls here when you wire your LLM; return a reordered list.
        # For now, return as-is.
        return candidates
