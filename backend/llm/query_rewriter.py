import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()


# ---------------------------------------------------------------------
# Regex fallback (unchanged)
# ---------------------------------------------------------------------
def regex_parse(query: str) -> dict:
    import re
    q = query.lower()
    duration = None
    m = re.search(r"(\d{1,3})\s*(?:minutes|mins|min)", q)
    if m:
        duration = int(m.group(1))

    seniority = None
    if any(word in q for word in ["entry", "junior", "graduate"]):
        seniority = "entry"
    elif any(word in q for word in ["senior", "lead", "manager", "director"]):
        seniority = "senior"
    elif any(word in q for word in ["mid", "experienced", "mid-level"]):
        seniority = "mid"

    skill_keywords = ["java", "python", "sql", "excel", "marketing", "sales", "seo", "selenium", "tableau"]
    skills = [k for k in skill_keywords if k in q]

    soft_keywords = ["communicat", "collaborat", "team", "stakeholder", "leadership"]
    softs = []
    for sk in soft_keywords:
        if sk in q:
            if sk == "communicat": softs.append("communication")
            elif sk == "collaborat": softs.append("collaboration")
            else: softs.append(sk)

    summary = query.strip()[:200]

    rewrite_parts = []
    if skills: rewrite_parts.append("SKILL: " + ", ".join(skills))
    if softs: rewrite_parts.append("SOFT: " + ", ".join(softs))
    if seniority: rewrite_parts.append("JOBLEVEL: " + seniority)
    if duration: rewrite_parts.append(f"DURATION: {duration}MIN")
    rewrite_parts.append(summary)

    return {
        "skills": ", ".join(skills) if skills else None,
        "soft_skills": ", ".join(softs) if softs else None,
        "seniority": seniority,
        "duration_minutes": duration,
        "languages": None,
        "summary": summary,
        "rewrite": " \n ".join(rewrite_parts)
    }


GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_REWRITER = "gemini-2.5-flash"

def llm_rewrite(query: str, fallback: bool = False):
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)],
        )
    ]

    config = types.GenerateContentConfig(
        temperature=0.1,
        top_p=1,
        max_output_tokens=8192,
        thinking_config={"thinking_budget": 0},
        response_mime_type="application/json",
        response_schema=types.Schema(
            type=types.Type.OBJECT,
            required=[
                "skills", "soft_skills", "seniority",
                "duration_minutes", "languages",
                "summary", "rewrite"
            ],
            properties={
                "skills": types.Schema(type=types.Type.STRING, nullable=True),
                "soft_skills": types.Schema(type=types.Type.STRING, nullable=True),
                "seniority": types.Schema(
                    type=types.Type.STRING,
                    enum=["entry", "mid", "senior", "any"],
                    nullable=True
                ),
                "duration_minutes": types.Schema(
                    type=types.Type.INTEGER,
                    nullable=True
                ),
                "languages": types.Schema(
                    type=types.Type.STRING,
                    nullable=True
                ),
                "summary": types.Schema(type=types.Type.STRING),
                "rewrite": types.Schema(type=types.Type.STRING),
            }
        )
    )

    try:
        response = client.models.generate_content(
            model=MODEL_REWRITER,
            contents=contents,
            config=config
        )

        parsed = json.loads(response.text)

        # ---- ADD STRUCTURED REWRITE FORMAT ----
        rewrite_parts = []

        if parsed.get("skills"):
            rewrite_parts.append(f"SKILL: {parsed['skills']}")
        if parsed.get("soft_skills"):
            rewrite_parts.append(f"SOFT: {parsed['soft_skills']}")
        if parsed.get("seniority"):
            rewrite_parts.append(f"JOBLEVEL: {parsed['seniority']}")
        if parsed.get("duration_minutes"):
            rewrite_parts.append(f"DURATION: {parsed['duration_minutes']}MIN")
        if parsed.get("languages"):
            rewrite_parts.append(f"LANG: {parsed['languages']}")

        # Always include summary last
        rewrite_parts.append(f"SUMMARY: {parsed.get('summary', '')}")

        parsed["rewrite"] = " \n ".join(rewrite_parts)
        # ----------------------------------------

        return parsed

    except Exception as e:
        if fallback:
            return regex_parse(query)
        raise
