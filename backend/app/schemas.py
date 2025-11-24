from pydantic import BaseModel, Field
from typing import Optional, List

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User's search query")
    top_k: Optional[int] = Field(10, ge=1, le=50, description="Number of results to return")

class Assessment(BaseModel):
    url: str
    name: str
    adaptive_support: str
    description: str
    duration: int
    remote_support: str
    test_type: List[str]

class RecommendationResponse(BaseModel):
    recommended_assessments: List[Assessment]
