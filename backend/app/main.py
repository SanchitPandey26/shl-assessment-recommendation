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
        
        # Format response to match simplified schema
        formatted_assessments = []
        for result in final_results:
            meta = result.get('meta', {})
            
            # Get duration (prefer single value or average, ensure int)
            duration_min = meta.get('duration_min')
            duration_max = meta.get('duration_max')
            if duration_max:
                duration = int(duration_max)
            elif duration_min:
                duration = int(duration_min)
            else:
                duration = 0  # Default to 0 if no duration info
            
            # Get test types
            test_types = meta.get('test_types', [])
            if isinstance(test_types, list):
                test_type_names = [t.get('name', str(t)) if isinstance(t, dict) else str(t) for t in test_types]
            else:
                test_type_names = [str(test_types)] if test_types else []
            
            formatted_assessments.append({
                "url": result.get('url', ''),
                "name": meta.get('name', ''),
                "adaptive_support": "Yes" if meta.get('adaptive_support') else "No",
                "description": meta.get('description', '')[:200] + "..." if meta.get('description', '') else '',
                "duration": duration,
                "remote_support": "Yes" if meta.get('remote_support') else "No",
                "test_type": test_type_names
            })
        
        return RecommendationResponse(
            recommended_assessments=formatted_assessments
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
