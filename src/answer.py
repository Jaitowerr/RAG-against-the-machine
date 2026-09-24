from pathlib import Path
from .search import Search
from .models import MinimalSource


class Answer(Search):
    """Answers one query using the retrieved chunks."""

    def __init__(self, query: str, k: int = 5) -> None:
        super().__init__(query, k)

    def retrieve_sources(self) -> list[MinimalSource]:
        """Run the inherited search and return the top-k sources."""
        self.prepare()
        return self.search()