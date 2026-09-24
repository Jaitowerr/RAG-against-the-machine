from pathlib import Path
from .search import Search
from .models import MinimalSource


class Answer(Search):
    """Answers one query using the retrieved chunks."""

    def __init__(self, query: str, k: int = 5) -> None:
        super().__init__(query, k)

    def retrieve_sources(self) -> list[MinimalSource]:
        """Run the inherited search and return the top-k sources."""
        self.prepare()  #carga el índice y tokeniza,
        return self.search()    #evuelve el top-k como MinimalSource

    def build_context(self) -> str:
        """Build one context string from the retrieved sources."""
        sources = self.retrieve_sources()

        chunks = []
        for source in sources:
            chunks.append(self._chunk_text(source))

        return "\n\n".join(chunks)

    def _chunk_text(self, source: MinimalSource) -> str:
        """Return the indexed text of one retrieved source."""
        for entry in self.entries:
            if (
                entry["file_path"] == source.file_path
                and entry["first_character_index"] == source.first_character_index
                and entry["last_character_index"] == source.last_character_index
            ):
                return str(entry.get("text", ""))
        return ""