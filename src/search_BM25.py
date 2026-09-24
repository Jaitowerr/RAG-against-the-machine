from rank_bm25 import BM25Okapi

from .models import MinimalSource
from .search import Search


class SearchLibBM25(Search):
    """Searches the indexed chunks with the rank-bm25 library."""

    def prepare(self) -> None:
        """Load the index and build the BM25Okapi model."""
        self.load_index()
        self._tokenize_query()
        self._tokenize_index()
        self.bm25 = BM25Okapi(self.tokens, k1=0.6 , b=0.99)

    def search(self, query: str | None = None) -> list[MinimalSource]:
        """Return the k most relevant sources for the given query."""
        if query is not None:
            self.query = query
            self.query_tokens = self._tokenize(query)

        scores = self.bm25.get_scores(self.query_tokens)
        matched_indices = [i for i, score in enumerate(scores) if score > 0.0]
        ranked_indices = sorted(
            matched_indices,
            key=lambda i: scores[i],
            reverse=True,
        )

        results: list[MinimalSource] = []
        for chunk_index in ranked_indices[: self.k]:
            entry = self.entries[chunk_index]
            results.append(
                MinimalSource(
                    file_path=entry["file_path"],
                    first_character_index=entry["first_character_index"],
                    last_character_index=entry["last_character_index"],
                )
            )
        return results