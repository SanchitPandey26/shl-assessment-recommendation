from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import QueryRequest, RecommendationResponse
from app.retriever import retrieve_assessments
from app.reranker import rerank_results

app = FastAPI(
    title="SHL Assessment Recommendation API",
    description="AI-powered assessment recommendation system",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "SHL Assessment Recommender"}

@app.post("/recommend", response_model=RecommendationResponse)
def recommend(payload: QueryRequest):
    """
    Get assessment recommendations based on a query.
    
    Args:
        payload: QueryRequest with user query and optional top_k
    
    Returns:
        RecommendationResponse with ranked assessments
    """
    try:
        # Step 1: Retrieve candidates
        raw_results = retrieve_assessments(payload.query, top_k=40)
        
        # Step 2: Rerank candidates
        final_results = rerank_results(
            payload.query, 
            raw_results, 
            top_k=payload.top_k
        )
        
        return RecommendationResponse(
            query=payload.query,
            rewritten_query=raw_results["rewritten_query"],
            assessments=final_results,
            total_results=len(final_results)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
