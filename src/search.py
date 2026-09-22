import json
import re
from pathlib import Path
from tqdm import tqdm
from collections import Counter
import math
from .models import MinimalSource


class Search:
    """Searches the indexed chunks."""

    def __init__(
        self,
        query: str,
        k: int = 5,
        index_path: Path = Path("data/processed/index.json"),
    ) -> None:
        self.query = query
        self.k = k
        self.index_path = index_path
        self.entries: list[dict] = []
        self.tokens: list[list[str]] = []
        self.term_freqs: list[Counter[str]] = []    #Esto guardará un contador para cada chunk.
        self.doc_freq: dict[str, int] = {}  #El numero de chunks que aparecen esas palabras, No significa que aparezca 4.703 veces en total sino en cuentos chunk
        self.query_tokens: list[str] = []
        self.average_chunk_length: float = 0.0

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Convert text into lowercase words."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def load_index(self) -> list[dict]:
        """Load the indexed chunks from the JSON file."""
        try:
            if not self.index_path.is_file():
                raise ValueError(
                    f"Index file does not exist: {self.index_path}"
                )
            entries = json.loads(
                self.index_path.read_text(encoding="utf-8")
            )
            if not isinstance(entries, list):
                raise ValueError(
                    f"Index file is malformed: {self.index_path}"
                )
            if not entries:
                raise ValueError(
                    f"Index is empty: {self.index_path}"
                )
            self.entries = entries
            return entries
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"Index file cannot be read: {self.index_path}"
            ) from error
    
    def _tokenize_index(self) -> None:
        """Tokenize the text of every indexed chunk."""
        self.tokens = []
        for entry in tqdm(self.entries, desc="Tokenizando chunks"):
            text = str(entry.get("text", ""))
            self.tokens.append(self._tokenize(text))

    def _count_terms(self) -> None:
        """Count term frequencies per chunk and document frequencies per term."""
        self.term_freqs = []
        self.doc_freq = {}
        for tokens in self.tokens:
            counts = Counter(tokens)
            self.term_freqs.append(counts)
            for term in counts:
                self.doc_freq[term] = self.doc_freq.get(term, 0) + 1

    def prepare(self) -> None:
        """Load and prepare the index for searching."""
        self.load_index()
        self._tokenize_query()
        self._tokenize_index()
        self._count_terms()
        self.average_chunk_length = self._average_chunk_length()

    def _tokenize_query(self) -> None:
        """Tokenize the search query."""
        self.query_tokens = self._tokenize(self.query)

    def _count_matching_terms(self, chunk_index: int) -> int:
        """Count query terms found in one indexed chunk."""
        chunk_terms = self.term_freqs[chunk_index]

        return sum(
            1
            for term in self.query_tokens
            if term in chunk_terms
        )

    def _average_chunk_length(self) -> float:
        """Calculate the average number of tokens per indexed chunk."""
        if not self.tokens:
            return 0.0
        total_tokens = sum(len(chunk_tokens) for chunk_tokens in self.tokens)
        return total_tokens / len(self.tokens)

    def _idf(self, term: str) -> float:
        """Calculate the BM25 inverse document frequency of a term."""
        doc_frequency = self.doc_freq.get(term, 0)
        total_chunks = len(self.entries)

        return math.log(
            (total_chunks - doc_frequency + 0.5) / (doc_frequency + 0.5) + 1
        )

    def _score_chunk(
        self,
        chunk_index: int,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> float:
        """Calculate the BM25 score of one chunk for the current query."""
        term_freqs = self.term_freqs[chunk_index]
        chunk_length = len(self.tokens[chunk_index])
        average_length = self.average_chunk_length

        if average_length == 0:
            return 0.0

        score = 0.0
        for term in self.query_tokens:
            frequency = term_freqs[term]
            if frequency == 0:
                continue

            idf = self._idf(term)
            length_normalization = k1 * (
                1 - b + b * chunk_length / average_length
            )
            score += idf * frequency * (k1 + 1) / (
                frequency + length_normalization
            )
        return score

    def search(self, query: str | None = None) -> list[MinimalSource]:
        """Return the k most relevant sources for the given query."""
        if query is not None:
            self.query = query
            self.query_tokens = self._tokenize(query)

        ranked_indices = sorted(
            range(len(self.entries)),
            key=self._score_chunk,
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
