from pydantic import BaseModel, Field
from typing import Optional, List, Any

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User's search query")
    top_k: Optional[int] = Field(10, ge=1, le=50, description="Number of results to return")

class RecommendationResponse(BaseModel):
    query: str
    rewritten_query:str
    assessments: List[dict]  # Using dict instead of strict schema
    total_results: int
