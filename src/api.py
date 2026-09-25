from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .models import MinimalSource
from .search import Search


class SearchRequest(BaseModel):
    """Body of a POST /search request."""

    query: str
    k: int = 5


app = FastAPI(
    title="RAG against the machine",
    description="Local HTTP API over the BM25 index.",
)

# @app.post("/search")  le dice a FastAPI: Cuando recibas una petición POST dirigida a /search, ejecuta la función que viene justo debajo.

@app.post("/search", response_model=list[MinimalSource])
def search_sources(request: SearchRequest) -> list[MinimalSource]:
    """Return the top-k sources for one query."""
    print(f"Petición recibida: query={request.query!r}, k={request.k}")
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=400,
            detail="query must not be empty.",
        )
    if request.k <= 0:
        raise HTTPException(
            status_code=400,
            detail="k must be greater than 0.",
        )
    try:
        searcher = Search(query, request.k)
        searcher.prepare()
        results = searcher.search()
        print(f"Resultados devueltos: {len(results)}")
        return results
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
