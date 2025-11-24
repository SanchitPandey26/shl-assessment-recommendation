from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import QueryRequest, RecommendationResponse
from app.retriever import retrieve_assessments
from app.reranker import rerank_results

app = FastAPI(
    title="SHL Assessment Recommendation API",
    description="AI-powered assessment recommendation engine",
    version="1.0.0"
)

# ---------------------------------------------------------
# CORS CONFIG (INCLUDE YOUR VERCEL URL)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://shl-assessment-recommendation.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SHL Assessment Recommender"
    }

# ---------------------------------------------------------
# Main recommend endpoint
# ---------------------------------------------------------
@app.post("/recommend", response_model=RecommendationResponse)
def recommend(payload: QueryRequest):
    try:
        raw_results = retrieve_assessments(
            payload.query,
            top_k=40
        )

        final_results = rerank_results(
            payload.query,
            raw_results,
            top_k=payload.top_k
        )

        formatted_assessments = []
        for result in final_results:
            meta = result.get("meta", {})

            duration_min = meta.get("duration_min")
            duration_max = meta.get("duration_max")
            duration = int(duration_max or duration_min or 0)

            test_types = meta.get("test_types", [])
            if isinstance(test_types, list):
                test_type_names = [
                    t.get("name", str(t)) if isinstance(t, dict)
                    else str(t)
                    for t in test_types
                ]
            else:
                test_type_names = [str(test_types)]

            formatted_assessments.append({
                "url": result.get("url", ""),
                "name": meta.get("name", ""),
                "adaptive_support": "Yes" if meta.get("adaptive_support") else "No",
                "description": meta.get("description", "")[:200] + "...",
                "duration": duration,
                "remote_support": "Yes" if meta.get("remote_support") else "No",
                "test_type": test_type_names
            })

        return RecommendationResponse(
            recommended_assessments=formatted_assessments
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {e}"
        )
