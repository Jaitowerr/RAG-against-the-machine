from pathlib import Path
from .search import Search


class Answer:
    """Answers one query using the retrieved chunks."""

    def __init__(self, query: str, k: int = 5) -> None:
        self.query = query
        self.k = k
        self.searcher = Search(query, k)
