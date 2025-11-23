import json
from pathlib import Path
import re
import unicodedata
import hashlib

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_PATH = BASE_DIR / "data" / "shl_catalog_raw.json"
CLEAN_PATH = BASE_DIR / "data" / "shl_catalog_clean.json"

TEST_TYPE_MAP = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competencies",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}

def normalize_text(s: str) -> str:
    if s is None:
        return None
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def bool_from_yesno(v):
    if v is None:
        return None
    v = str(v).strip().lower()
    if v in ("yes", "y", "true", "1"):
        return True
    if v in ("no", "n", "false", "0"):
        return False
    return None

def canonical_url(url: str) -> str:
    if not url:
        return None
    return url.strip()

def make_id(item: dict) -> str:
    url = item.get("url")
    base = url if url else (item.get("name","") + "|" + (item.get("description") or ""))
    h = hashlib.sha1(str(base).encode("utf-8")).hexdigest()
    return f"shl_{h[:12]}"

def expand_test_types(codes):
    if not codes:
        return []
    out = []
    for c in codes:
        parts = re.split(r"[,/;\s]+", str(c))
        for p in parts:
            p = p.strip().upper()
            if not p:
                continue
            out.append({
                "code": p,
                "name": TEST_TYPE_MAP.get(p, p)
            })
    # dedupe preserving order
    seen = set()
    dedup = []
    for e in out:
        key = (e["code"], e["name"])
        if key not in seen:
            seen.add(key)
            dedup.append(e)
    return dedup

def extract_keywords(text, top_n=12):
    """Very lightweight keyword extractor: finds common alpha words and returns unique top_n."""
    if not text:
        return []
    words = re.findall(r"[A-Za-z]{3,}", text.lower())
    # frequency order
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in sorted_words[:top_n]]

def normalize_joblevels(jl: str):
    if not jl:
        return []
    parts = [normalize_text(p) for p in re.split(r"[,\|;/]", jl) if p and p.strip()]
    out = []
    for p in parts:
        pnorm = p.lower()
        # canonical mapping (few examples)
        if "entry" in pnorm or "graduate" in pnorm:
            out.append("entry-level")
        elif "manager" in pnorm or "supervisor" in pnorm:
            out.append("manager")
        elif "executive" in pnorm or "director" in pnorm:
            out.append("senior")
        elif "professional" in pnorm or "mid" in pnorm:
            out.append("mid-professional")
        else:
            out.append(pnorm.replace(" ", "-"))
    return list(dict.fromkeys(out))

def extract_tags(item):
    tags = set()
    for tt in item.get("test_type_expanded", []):
        tags.add(tt["name"])
    jl = item.get("job_levels")
    if jl:
        for part in re.split(r"[,\|;/]", jl):
            p = normalize_text(part)
            if p:
                tags.add(p)
    name = item.get("name") or ""
    words = re.findall(r"[A-Za-z]{3,}", name)
    for w in words[:8]:
        tags.add(w)
    for c in (item.get("test_type_codes") or []):
        tags.add(str(c).strip())
    return sorted({t.strip() for t in tags if t and len(t.strip())>0})

def build_structured_embed_text(item):
    parts = []
    if item.get("name"):
        parts.append(item["name"])
    if item.get("description"):
        parts.append(item["description"])
    # structured tokens
    # Test types
    if item.get("test_type_expanded"):
        types = " ".join([t["name"] for t in item["test_type_expanded"]])
        parts.append("TYPE: " + types)
    # job levels
    if item.get("job_levels"):
        jls = normalize_joblevels(item.get("job_levels"))
        if jls:
            parts.append("JOBLEVEL: " + " ".join(jls))
    # languages
    if item.get("languages"):
        if isinstance(item["languages"], list):
            parts.append("LANG: " + " ".join(item["languages"]))
        else:
            parts.append("LANG: " + str(item["languages"]))
    # duration
    dm = item.get("duration_min")
    dx = item.get("duration_max")
    if dm is not None and dx is not None:
        if dm == dx:
            parts.append(f"DURATION: {dm}MIN")
        else:
            parts.append(f"DURATION: {dm}-{dx}MIN")
    elif dm is not None:
        parts.append(f"DURATION: {dm}MIN")
    # keywords from description/name for skill tokens
    kw = extract_keywords(" ".join([item.get("name",""), item.get("description","")]), top_n=10)
    if kw:
        parts.append("SKILL: " + " ".join(kw))
    # tags
    if item.get("tags"):
        if isinstance(item["tags"], list):
            parts.append("TAGS: " + " ".join(item["tags"]))
        else:
            parts.append("TAGS: " + str(item["tags"]))
    return " \n ".join(parts)

def clean_catalog():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw catalog not found at: {RAW_PATH}")

    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    cleaned = []
    url_seen = set()
    name_desc_seen = set()

    for rec in raw:
        name = normalize_text(rec.get("name"))
        url = canonical_url(rec.get("url"))
        desc = normalize_text(rec.get("description") or rec.get("summary") or "")
        job_levels = normalize_text(rec.get("job_levels") or rec.get("job level") or rec.get("job-levels"))
        remote_support = bool_from_yesno(rec.get("remote_support"))
        adaptive_support = bool_from_yesno(rec.get("adaptive_support"))

        languages = rec.get("languages") or None
        if isinstance(languages, list):
            languages = [normalize_text(l) for l in languages if l]

        duration_min = rec.get("duration_min")
        duration_max = rec.get("duration_max")

        test_type_codes = rec.get("test_type_codes") or rec.get("test_type") or []
        if isinstance(test_type_codes, str):
            test_type_codes = re.split(r"[,/;\s]+", test_type_codes)

        test_type_expanded = expand_test_types(test_type_codes)

        # dedupe
        if url:
            if url in url_seen:
                continue
            url_seen.add(url)
        else:
            key = f"{name}::{desc}"
            if key in name_desc_seen:
                continue
            name_desc_seen.add(key)

        item = {
            "id": make_id({"url": url, "name": name, "description": desc}),
            "name": name,
            "url": url,
            "description": desc,
            "job_levels": job_levels,
            "languages": languages,
            "duration_min": duration_min,
            "duration_max": duration_max,
            "remote_support": remote_support,
            "adaptive_support": adaptive_support,
            "test_type_codes": list(map(lambda x: x.strip(), test_type_codes)) if test_type_codes else [],
            "test_type_expanded": test_type_expanded,
        }

        item["tags"] = extract_tags(item)
        item["embed_text"] = build_structured_embed_text(item)

        cleaned.append(item)

    with open(CLEAN_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print("Cleaning complete")
    print(f"  raw_count  = {len(raw)}")
    print(f"  clean_count= {len(cleaned)}")
    print(f"  saved -> {CLEAN_PATH}")

if __name__ == "__main__":
    clean_catalog()
