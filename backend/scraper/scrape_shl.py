import requests
from bs4 import BeautifulSoup
import json
import time
from tqdm import tqdm
import random
from urllib.parse import urljoin
from pathlib import Path
import re

BASE_URL = "https://www.shl.com"
CATALOG_URL = BASE_URL + "/products/product-catalog/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

OUT_DIR = Path(__file__).resolve().parents[1] / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_PATH = OUT_DIR / "shl_catalog_raw.json"

PAGE_SIZE = 12
TIMEOUT = 15
RETRIES = 3
DELAY = 0.8


def fetch_catalog_page(start: int) -> str:
    params = {"start": start, "type": 1, "type": 1}
    for attempt in range(RETRIES):
        try:
            resp = requests.get(
                CATALOG_URL,
                headers=HEADERS,
                params=params,
                timeout=TIMEOUT
            )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"[WARN] retry {attempt+1}/{RETRIES} for start={start}: {e}")
            time.sleep(1.5)
    raise RuntimeError(f"Failed to fetch page start={start}")


def parse_catalog_rows(html: str):
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("tr[data-entity-id]")
    items = []

    for row in rows:
        a_tag = row.select_one("td.custom__table-heading__title a")
        if not a_tag:
            continue

        name = a_tag.get_text(strip=True)
        href = a_tag.get("href")
        if not href:
            continue

        if "pre-packaged" in href.lower():
            continue

        full_url = urljoin(BASE_URL, href)

        general_cols = row.select("td.custom__table-heading__general")

        remote_support = "Yes" if general_cols and general_cols[0].select_one(".catalogue__circle.-yes") else "No"
        adaptive_support = "Yes" if len(general_cols) > 1 and general_cols[1].select_one(".catalogue__circle.-yes") else "No"

        codes = [span.get_text(strip=True) for span in row.select(".product-catalogue__key")]

        items.append({
            "name": name,
            "url": full_url,
            "remote_support": remote_support,
            "adaptive_support": adaptive_support,
            "test_type_codes": codes,
        })

    return items


def fetch_detail_page(url: str):
    """
    Extracts:
      - description
      - job_levels
      - languages (list)  <-- NEW
      - duration_min, duration_max (ints or None)  <-- NEW
    The function is robust to multiple HTML layouts and uses fallbacks.
    """
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "lxml")

            # --- Description (existing logic with fallbacks) ---
            description = None
            desc_h4 = soup.find(lambda tag: tag.name == "h4" and "description" in tag.get_text(strip=True).lower())
            if desc_h4:
                p = desc_h4.find_next("p")
                if p:
                    description = p.get_text(" ", strip=True)

            if not description:
                block = soup.select_one(".product-description")
                if block:
                    description = block.get_text(" ", strip=True)

            if not description:
                block = soup.select_one(".wysiwyg")
                if block:
                    description = block.get_text(" ", strip=True)

            # --- Job levels (existing) ---
            job_levels = None
            h4_job = soup.find(lambda tag: tag.name == "h4" and "job levels" in tag.get_text(strip=True).lower())
            if h4_job:
                p = h4_job.find_next("p")
                if p:
                    job_levels = p.get_text(" ", strip=True)

            # --- Languages (NEW) ---
            languages = None
            h4_lang = soup.find(lambda tag: tag.name == "h4" and "language" in tag.get_text(strip=True).lower())
            if h4_lang:
                p = h4_lang.find_next("p")
                if p:
                    # split by commas and normalize
                    langs = [l.strip() for l in re.split(r"[,/;]+", p.get_text(" ", strip=True)) if l.strip()]
                    languages = langs if langs else None

            # Sometimes languages are present in downloads but we should NOT use download language.
            # We only use explicit 'Languages' field (as above).

            # --- Duration / Assessment length (NEW) ---
            duration_min = None
            duration_max = None

            # Look for an h4 that mentions length/time or 'Assessment length'
            possible_time_labels = ["assessment length", "approximate completion time", "completion time", "duration", "time"]
            time_paragraph_texts = []

            # First try: h4 with 'Assessment length' as in provided HTML
            h4_time = soup.find(lambda tag: tag.name == "h4" and any(lbl in tag.get_text(strip=True).lower() for lbl in ["assessment length", "assessment time", "completion time", "duration", "approximate completion time"]))
            if h4_time:
                # get next <p> text
                p = h4_time.find_next("p")
                if p:
                    time_paragraph_texts.append(p.get_text(" ", strip=True))

            # Fallback: search for any p that contains "Approximate Completion Time" or "minutes"
            for p in soup.find_all("p"):
                txt = p.get_text(" ", strip=True)
                if re.search(r"minute", txt, flags=re.I) or re.search(r"approximate completion time", txt, flags=re.I) or re.search(r"completion time", txt, flags=re.I):
                    time_paragraph_texts.append(txt)

            # Also search whole page for patterns like "X minutes" or "X–Y minutes"
            page_text = soup.get_text(" ", strip=True)
            # collect unique candidates
            time_paragraph_texts = list(dict.fromkeys(time_paragraph_texts))  # preserve order, unique

            # parse candidate texts for numbers
            def parse_minutes_from_text(t):
                # patterns:
                # "Approximate Completion Time in minutes = 30"
                m = re.search(r"approximate completion time.*?=\s*([\d]{1,4})", t, flags=re.I)
                if m:
                    val = int(m.group(1))
                    return (val, val)
                # "30 minutes" or "30 min"
                m2 = re.search(r"(\d{1,3})\s*(?:-|\u2013|\u2014|\sto\s|\s)?\s*(\d{1,3})?\s*(?:minutes|mins|min)\b", t, flags=re.I)
                if m2:
                    a = int(m2.group(1))
                    b = m2.group(2)
                    if b:
                        b = int(b)
                    else:
                        b = a
                    # ensure min <= max
                    mn, mx = (min(a, b), max(a, b))
                    return (mn, mx)
                # patterns like "Approximate Completion Time in minutes: 30" or "Time = 30 minutes"
                m3 = re.search(r"(\d{1,3})\s*minutes", t, flags=re.I)
                if m3:
                    v = int(m3.group(1))
                    return (v, v)
                return None

            # Try parsing the collected paragraphs first
            parsed = None
            for cand in time_paragraph_texts:
                parsed = parse_minutes_from_text(cand)
                if parsed:
                    duration_min, duration_max = parsed
                    break

            # If not found, try searching the page text for common patterns
            if duration_min is None:
                parsed = parse_minutes_from_text(page_text)
                if parsed:
                    duration_min, duration_max = parsed

            # final normalize: ensure ints or None
            if duration_min is not None:
                try:
                    duration_min = int(duration_min)
                except:
                    duration_min = None
            if duration_max is not None:
                try:
                    duration_max = int(duration_max)
                except:
                    duration_max = None

            # --- Return collected fields ---
            return {
                "description": description,
                "job_levels": job_levels,
                "languages": languages,
                "duration_min": duration_min,
                "duration_max": duration_max,
            }

        except Exception as e:
            print(f"[WARN] detail retry {attempt+1}/{RETRIES} for {url}: {e}")
            time.sleep(1.5)

    print(f"[ERROR] failed detail page {url}")
    return {}

def run_scraper():
    print("🔍 Starting SHL scraper...")

    all_items = []
    start = 0

    while True:
        print(f"➡ Fetching page start={start}")
        html = fetch_catalog_page(start)

        page_items = parse_catalog_rows(html)
        print(f"   → Found {len(page_items)} items on this page.")

        if len(page_items) == 0:
            break

        all_items.extend(page_items)
        start += PAGE_SIZE
        time.sleep(DELAY)

    print(f"\n📦 Total items found across all pages: {len(all_items)}")

    # Fetch detail pages
    full_output = []
    for item in tqdm(all_items, desc="🔗 Scraping detail pages"):
        detail = fetch_detail_page(item["url"])
        # merge fields into item (don't overwrite existing keys)
        merged = {**item, **detail}
        full_output.append(merged)
        time.sleep(0.5)

    # Save ONLY required fields
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Saved cleaned catalog to: {RAW_PATH}")
    print(f"   Count: {len(full_output)} items")


if __name__ == "__main__":
    run_scraper()
