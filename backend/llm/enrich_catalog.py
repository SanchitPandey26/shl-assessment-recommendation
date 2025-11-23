import json
import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_PATH = BASE_DIR / "data" / "shl_catalog_clean.json"
ENRICHED_PATH = BASE_DIR / "data" / "shl_catalog_enriched.json"

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

def enrich_item(item):
    prompt = f"""
    You are an expert in SHL assessments and I/O psychology.
    Analyze the following assessment and provide rich metadata to improve search retrieval.

    Assessment Name: {item.get('name')}
    Description: {item.get('description')}
    Test Types: {json.dumps(item.get('test_type_expanded'))}
    Job Levels: {item.get('job_levels')}

    Output a JSON object with the following fields:
    - "skills": List of specific technical and soft skills measured (e.g. "Java", "Communication", "Numerical Reasoning").
    - "synonyms": List of alternative names or related terms for this test.
    - "summary": A concise 1-2 sentence summary optimized for search matching.
    - "synthetic_queries": List of 5-8 natural language queries that a recruiter might type to find this test. Vary the phrasing (e.g. "test for java dev", "assess coding skills", "hiring a manager").

    JSON Output:
    """

    retries = 0
    max_retries = 5
    base_delay = 2

    while retries < max_retries:
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                    response_schema=types.Schema(
                        type=types.Type.OBJECT,
                        required=["skills", "synonyms", "summary", "synthetic_queries"],
                        properties={
                            "skills": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                            "synonyms": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                            "summary": types.Schema(type=types.Type.STRING),
                            "synthetic_queries": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                        }
                    )
                )
            )
            return json.loads(response.text)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                delay = base_delay * (2 ** retries)
                print(f"Rate limit hit for {item.get('name')}. Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
            else:
                print(f"Error enriching {item.get('name')}: {e}")
                return None
    return None

def main():
    if not CLEAN_PATH.exists():
        print(f"Clean catalog not found at {CLEAN_PATH}")
        return

    with open(CLEAN_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    enriched_catalog = []
    
    # Check if we have partial progress
    if ENRICHED_PATH.exists():
        with open(ENRICHED_PATH, "r", encoding="utf-8") as f:
            enriched_catalog = json.load(f)
            print(f"Loaded {len(enriched_catalog)} already enriched items.")
    
    processed_ids = {item["id"] for item in enriched_catalog}
    
    total = len(catalog)
    print(f"Starting enrichment for {total} items...")

    for i, item in enumerate(catalog):
        if item["id"] in processed_ids:
            continue

        print(f"[{i+1}/{total}] Enriching: {item.get('name')}")
        
        enrichment = enrich_item(item)
        if enrichment:
            item["enrichment"] = enrichment
            enriched_catalog.append(item)
        else:
            # If failed, just keep original item but maybe mark as failed? 
            # For now, we just append the original item without enrichment to avoid data loss
            # or better, retry? Let's just skip enrichment for this run to keep it simple.
            enriched_catalog.append(item)

        # Save every 10 items
        if len(enriched_catalog) % 10 == 0:
            with open(ENRICHED_PATH, "w", encoding="utf-8") as f:
                json.dump(enriched_catalog, f, indent=2, ensure_ascii=False)
        
        # Rate limit protection
        time.sleep(0.5)

    # Final save
    with open(ENRICHED_PATH, "w", encoding="utf-8") as f:
        json.dump(enriched_catalog, f, indent=2, ensure_ascii=False)

    print(f"Enrichment complete. Saved to {ENRICHED_PATH}")

if __name__ == "__main__":
    main()
