from fastapi import FastAPI
from pydantic import BaseModel
from retriever import retrieve_assessments
from reranker import rerank_results

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/recommend")
def recommend(payload: QueryRequest):
    raw_results = retrieve_assessments(payload.query)
    final_results = rerank_results(payload.query, raw_results)
    return {"query": payload.query, "assessments": final_results}
