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
    return v in ("yes", "y", "true", "1")

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
    # dedupe
    seen = set()
    dedup = []
    for e in out:
        key = (e["code"], e["name"])
        if key not in seen:
            seen.add(key)
            dedup.append(e)
    return dedup

def extract_tags(item):
    tags = set()

    for tt in item.get("test_type_expanded", []):
        tags.add(tt["name"])

    if item.get("job_levels"):
        for part in re.split(r"[,\|;/]", item["job_levels"]):
            p = normalize_text(part)
            if p:
                tags.add(p)

    if item.get("languages"):
        for lang in item["languages"]:
            tags.add(lang)

    name = item.get("name") or ""
    words = re.findall(r"[A-Za-z]{3,}", name)
    for w in words[:8]:
        tags.add(w)

    for c in item.get("test_type_codes") or []:
        tags.add(str(c).strip())

    return sorted(t.lower() for t in tags if t.strip())

def clean_catalog():
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    cleaned = []
    url_seen = set()
    name_desc_seen = set()

    for rec in raw:
        name = normalize_text(rec.get("name"))
        url = canonical_url(rec.get("url"))
        desc = normalize_text(rec.get("description"))
        job_levels = normalize_text(rec.get("job_levels"))
        remote_support = bool_from_yesno(rec.get("remote_support"))
        adaptive_support = bool_from_yesno(rec.get("adaptive_support"))

        languages = rec.get("languages") or None
        if isinstance(languages, list):
            languages = [normalize_text(l) for l in languages if l]

        duration_min = rec.get("duration_min")
        duration_max = rec.get("duration_max")

        test_type_codes = rec.get("test_type_codes") or []
        if isinstance(test_type_codes, str):
            test_type_codes = re.split(r"[,/;\s]+", test_type_codes)

        test_type_expanded = expand_test_types(test_type_codes)

        # dedupe logic
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
            "test_type_codes": test_type_codes,
            "test_type_expanded": test_type_expanded,
        }

        item["tags"] = extract_tags(item)

        parts = []
        if name: parts.append(name)
        if desc: parts.append(desc)
        if job_levels: parts.append(job_levels)
        if languages: parts.append(" ".join(languages))
        if test_type_expanded:
            parts.append(" ".join(t["name"] for t in test_type_expanded))

        if duration_min:
            parts.append(f"duration {duration_min} minutes")

        item["embed_text"] = " \n ".join(parts)

        cleaned.append(item)

    with open(CLEAN_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)

    print("Cleaning complete")
    print(f"raw_count  = {len(raw)}")
    print(f"clean_count= {len(cleaned)}")

if __name__ == "__main__":
    clean_catalog()
