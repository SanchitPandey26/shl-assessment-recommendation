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

    # --- IMPROVED RERANK PROMPT FOR COMBINATION QUERIES ---
    weighted_prompt = """
You are an expert at ranking assessment tests based on job requirements.

=========================
CRITICAL PRINCIPLE
=========================

**COMBINATION QUERIES**: If the query asks for MULTIPLE requirements (e.g., "Java + collaboration", "COO + cultural fit", "developer + analytical"),
you MUST prioritize tests that address BOTH/ALL requirements, or recommend a COMBINATION of complementary tests.

DO NOT over-rank tests that only match ONE dimension of multi-dimensional queries.

=========================
SCORING GUIDELINES
=========================

Assign final scores between 0 and 1.

Use these weights:

1. **REQUIREMENT COVERAGE — weight 0.45** (HIGHEST PRIORITY)
   - How many of the query's requirements does this test address?
   - Example: "Java + collaboration" → Java test alone = 50% coverage, Collaboration test alone = 50%, Both = 100%
   - Multi-requirement queries REQUIRE high coverage scores

2. **SKILL MATCH — weight 0.25** (IMPORTANT)
   - Does the test directly measure the PRIMARY skill?
   - For technical roles: prefer Knowledge & Skills (K), Simulations (S), or practical tests
   - For leadership/senior roles: include Personality & Behavior (P), Ability & Aptitude (A)

3. **TEST TYPE APPROPRIATENESS — weight 0.15**
   - Technical roles: Coding tests ("Automata"), Knowledge tests
   - Seni or/Executive: OPQ (Personality), Verify (Cognitive ability), Leadership reports
   - "Cultural fit": OPQ Personality Questionnaires
   - Entry-level: Simulations, basic knowledge tests

4. **DURATION ALIGNMENT — weight 0.10** (MODERATE)
   - Prefer tests within ±15 minutes of target
   - Duration is a TIE-BREAKER, not primary factor

5. **JOB LEVEL MATCH — weight 0.05**
   - Match seniority if specified

=========================
SPECIAL SCENARIOS
=========================

- **"Developer" + any role**: Boost "Automata" series (hands-on coding)
- **"Cultural fit" / "Personality"**: Boost OPQ tests (occupational-personality-questionnaire)
- **"Senior" / "Executive"**: Boost Verify (cognitive), OPQ-Leadership
- **"Collaboration" / "Communication"**: Include soft skills tests (interpersonal-communications, business-communication)

=========================
EXAMPLES (FEW-SHOT)
=========================

**Example 1: "Java developer + collaboration, 40 minutes"**
GOOD ranking:
1. Automata-Fix (Java coding) - 0.85 - "Hands-on Java coding, addresses primary skill"
2. Java 8 (Knowledge test) - 0.75 - "Core Java knowledge"
3. Interpersonal Communications - 0.65 - "Addresses collaboration requirement"

BAD ranking:
1. Java Platform EE 7 - 0.90 - "Java match but ignores duration (60min) and collaboration"
2. Core Java Advanced - 0.85 - "Perfect Java but no collaboration component"
3. Business Communication - 0.20 - "Collaboration but no Java"

**Example 2: "COO in China, cultural fit, 1 hour"**
GOOD ranking:
1. OPQ32r (Personality) - 0.90 - "Personality assessment for cultural fit"
2. Global Skills Assessment - 0.80 - "Cross-cultural competencies, leadership"
3. Operations Management (Knowledge) - 0.70 - "Domain knowledge for COO role"

BAD ranking:
1. Operations Management - 0.95 - "Domain match but ignores 'cultural fit' requirement"
2. Financial Accounting - 0.60 - "Tangential skill"
3. OPQ - 0.40 - "Low score despite being CRITICAL for cultural fit"

=========================
OUTPUT FORMAT
=========================

Return JSON ONLY:

{
  "results": [
    {"url": "...", "score": 0.87, "reason": "Covers X and Y requirements, appropriate test type"},
    ...
  ]
}

Rank by descending score. Begin now.
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
