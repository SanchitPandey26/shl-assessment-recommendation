import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_RERANK = "gemini-2.5-flash"


def llm_rerank(query: str, rewritten: str, candidates: list):
    """
    candidates = [
        {
            "url": "...",
            "name": "...",
            "desc": "...",
            "duration_min": int or None,
            "duration_max": int or None,
            "job_levels": "...",
            "languages": [...],
            "test_types": [...],
            "tags": [...]
        }
    ]
    """

    # --- Clean structured candidate list ---
    clean_list = []
    for c in candidates:
        clean_item = {
            "url": c["url"],
            "name": c.get("name", ""),
            "desc": c.get("desc", ""),
            "duration_min": c.get("duration_min"),
            "duration_max": c.get("duration_max"),
            "job_levels": c.get("job_levels"),
            "languages": c.get("languages"),
            "test_types": c.get("test_types"),
            "tags": c.get("tags"),
        }
        clean_list.append(clean_item)

    candidates_json = json.dumps(clean_list, ensure_ascii=False, indent=2)

    # --- WEIGHTED RERANK PROMPT INSERTED HERE ---
    weighted_prompt = """
You are an expert at ranking assessment tests based on job requirements.

=========================
SCORING GUIDELINES
=========================

Assign final scores between 0 and 1.

Use these weights:

1. SKILL MATCH — weight 0.50 (VERY IMPORTANT)
   - If the test does NOT directly measure the core skill (e.g., Java),
     its score must be significantly lower.
   - Skill match should dominate duration.

2. TEST TYPE RELEVANCE — weight 0.15
   - Prefer technical, coding, or "Knowledge & Skills" tests for technical roles.
   - Reduce score for cognitive/personality tests unless explicitly relevant.

3. DURATION ALIGNMENT — weight 0.15 (MODERATE IMPORTANCE)
   - Prefer tests within ±10 minutes of target duration.
   - Duration MUST NOT outweigh skill match.

4. JOB LEVEL MATCH — weight 0.10
   - If seniority is specified, match it.
   - If not specified, mid-level is neutral.

5. SOFT SKILLS — weight 0.05
   - Collaboration, teamwork, communication: small positive boost.

6. LANGUAGE & TAGS — weight 0.05
   - Small boost if languages or tags match the query context.

=========================
ADDITIONAL RULES
=========================

- NEVER rank a non-Java test above a Java assessment when the query requires Java skills.
- A cognitive ability test may appear, but ALWAYS lower than any Java-aligned test.
- Duration is a tie-breaker, not the primary factor.
- Provide a short reason for each scoring decision.

=========================
OUTPUT FORMAT
=========================

Return JSON ONLY:

{
  "results": [
    {"url": "...", "score": 0.87, "reason": "short reason"},
    ...
  ]
}

Begin now.
"""

    # --- Build Gemini request contents ---
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"QUERY:\n{query}")]
        ),
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"REWRITTEN:\n{rewritten}")]
        ),
        types.Content(
            role="user",
            parts=[types.Part.from_text(text="CANDIDATES_JSON:")]
        ),
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=candidates_json)]
        ),
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=weighted_prompt)]
        ),
    ]

    # --- Strict JSON response schema ---
    config = types.GenerateContentConfig(
        temperature=0.1,
        top_p=1,
        max_output_tokens=4096,
        thinking_config={"thinking_budget": 0},
        response_mime_type="application/json",
        response_schema=types.Schema(
            type=types.Type.OBJECT,
            required=["results"],
            properties={
                "results": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        required=["url", "score", "reason"],
                        properties={
                            "url": types.Schema(type=types.Type.STRING),
                            "score": types.Schema(type=types.Type.NUMBER),
                            "reason": types.Schema(type=types.Type.STRING),
                        },
                    ),
                )
            },
        ),
    )

    # --- Gemini LLM Call ---
    try:
        response = client.models.generate_content(
            model=MODEL_RERANK,
            contents=contents,
            config=config,
        )
        parsed = json.loads(response.text)
        return parsed["results"]

    except Exception:
        # Simple fallback ranking
        fallback = []
        for i, c in enumerate(clean_list):
            fallback.append({
                "url": c["url"],
                "score": 1 - 0.05 * i,
                "reason": "fallback"
            })
        return fallback
