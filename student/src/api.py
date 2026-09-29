from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .models import MinimalSource
from .search import Search

from .answer import Answer
from .models import AnsweredQuestion


class SearchRequest(BaseModel):
    """Body of a POST /search request."""

    query: str
    k: int = 5


class RagApi:
    """Holds the FastAPI app and registers every HTTP endpoint."""

    def __init__(self) -> None:
        """Create the app and register the routes on it."""
        self.app = FastAPI(
            title="RAG against the machine",
            description="Local HTTP API over the BM25 index.",
        )
        self.app.post(
            "/search",
            response_model=list[MinimalSource],
        )(self.search_sources)
        self.app.post(
            "/answer",
            response_model=AnsweredQuestion,
        )(self.answer_question)

    def search_sources(
        self,
        request: SearchRequest,
    ) -> list[MinimalSource]:
        """Return the top-k sources for one query."""
        print(
            f"Petición recibida: query={request.query!r}, "
            f"k={request.k}"
        )
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
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error

    def answer_question(
        self,
        request: SearchRequest,
    ) -> AnsweredQuestion:
        """Answer one query using the retrieved sources."""
        print(
            f"Petición de respuesta: query={request.query!r}, "
            f"k={request.k}"
        )
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
            answerer = Answer(query, request.k)
            context = answerer.build_context()
            if not context:
                raise HTTPException(
                    status_code=404,
                    detail=f"No sources found for {query!r}.",
                )
            prompt = answerer.build_prompt(context)
            result = answerer.generate_answers([prompt])[0]
            answered = AnsweredQuestion(
                question=query,
                sources=answerer.sources,
                answer=result,
            )
            print(f"Respuesta generada: {result[:80]!r}...")
            return answered
        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            ) from error


app = RagApi().app



