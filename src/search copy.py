import json
import re
from pathlib import Path
from .css import StyledBar
from collections import Counter
import math
from .models import MinimalSource


class Search:
    """Searches the indexed chunks."""

    

    def __init__(
        self,
        query: str,
        k: int = 5,
        # index_path: Path = Path("data/processed/index.json"),
        index_path: Path | None = None
    ) -> None:
        self.query = query
        self.k = k
        self.index_path = index_path
        self.entries: list[dict] = []
        self.tokens: list[list[str]] = []
        # Esto guardará un contador para cada chunk.
        self.term_freqs: list[Counter[str]] = []
        # El numero de chunks que aparecen esas palabras, No significa que aparezca 4.703 veces en total sino en cuentos chunk
        self.doc_freq: dict[str, int] = {}
        self.query_tokens: list[str] = []
        self.average_chunk_length: float = 0.0
        

    @staticmethod
    def _tokenize(text: str) -> list[str]:  #divide el texto en términos.
        """Convert text into lowercase words."""
        # return re.findall(r"[a-z0-9_]+|[-+=*&(){}\[\]]", text.lower())
        _CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
        return re.findall(r"[a-z0-9]+", _CAMEL_SPLIT.sub(" ", text).lower())    #Probar con este con _CAMEL_SPLIT o el de abajo el normal, comprobar con k=5
        # return re.findall(r"[a-z0-9]+", text.lower())   # lista de cadenas (list[str]

    # def load_index(self) -> list[dict]:
    def load_index(self) -> None:
        """Load the indexed chunks from one file or from every index file."""
        entries: list[dict] = []
        for index_file in self._resolve_index_files():
            try:
                if not index_file.is_file():
                    raise ValueError(
                        f"Index file does not exist: {index_file}"
                    )
                file_entries = json.loads(
                    index_file.read_text(encoding="utf-8")
                )
                if not isinstance(file_entries, list):
                    raise ValueError(
                        f"Index file is malformed: {index_file}"
                    )
                entries.extend(file_entries)
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError(
                    f"Index file cannot be read: {index_file}"
                ) from error
        if not entries:
            raise ValueError("Index is empty.")
        self.entries = entries
        # return entries

    # def load_index(self) -> list[dict]:
    #     """Load the indexed chunks from the JSON file."""
    #     try:
    #         if not self.index_path.is_file():
    #             raise ValueError(
    #                 f"Index file does not exist: {self.index_path}"
    #             )
    #         entries = json.loads(
    #             self.index_path.read_text(encoding="utf-8")
    #         )
    #         if not isinstance(entries, list):
    #             raise ValueError(
    #                 f"Index file is malformed: {self.index_path}"
    #             )
    #         if not entries:
    #             raise ValueError(
    #                 f"Index is empty: {self.index_path}"
    #             )
    #         self.entries = entries
    #         return entries
    #     except (OSError, json.JSONDecodeError) as error:
    #         raise ValueError(
    #             f"Index file cannot be read: {self.index_path}"
    #         ) from error

    def _tokenize_index(self) -> None:
        """Tokenize the text of every indexed chunk."""
        self.tokens = []
        for entry in StyledBar(self.entries, desc="Tokenizando chunks"):
            text = str(entry.get("text", ""))
            self.tokens.append(self._tokenize(text))

    def _count_terms(self) -> None: #calcula las frecuencias.
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
        self.load_index()   #lee los JSON y lo guarda lis de dicc, en memoria self.entries
        self._tokenize_query()  #Se tokeniza la consulta inicial
        self._tokenize_index()  #Recorre el texto de cada chunk y lo divide en palabras.Guarda el resultado en self.tokens
        self._count_terms() #Se calculan las frecuencias
        self.average_chunk_length = self._average_chunk_length() #Calcula la longitud media de los chunks para que BM25 pueda normalizar la puntuación según el tamaño de cada chunk.

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

    def _average_chunk_length(self) -> float:   #calcula la longitud media.
        """Calculate the average number of tokens per indexed chunk."""
        if not self.tokens:
            return 0.0
        total_tokens = sum(len(chunk_tokens) for chunk_tokens in self.tokens)
        return total_tokens / len(self.tokens)

    def _idf(self, term: str) -> float: #calcula el peso IDF
        """Calculate the BM25 inverse document frequency of a term."""
        doc_frequency = self.doc_freq.get(term, 0)
        total_chunks = len(self.entries)

        return math.log(
            (total_chunks - doc_frequency + 0.5) / (doc_frequency + 0.5) + 1
        )

    def _score_chunk(
        self,
        chunk_index: int,
        k1: float = 1.2,    #k1 bajo: la repetición del término se satura rápidamente. k1 alto: las repeticiones siguen aumentando más la puntuación.
        b: float = 0.45,    #Controla cuánto penaliza BM25 a los chunks largos. b = 0 → no se tiene en cuenta la longitud del chunk. b = 1 → se aplica la normalización completa por longitud.
    ) -> float: #calcula la puntuación BM25.
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

    def search(self, query: str | None = None) -> list[MinimalSource]:  #ordena y devuelve los mejores chunks
        """Return the k most relevant sources for the given query."""
        if query is not None:
            self.query = query
            self.query_tokens = self._tokenize(query)

        scores = [self._score_chunk(i) for i in range(len(self.entries))]
        matched_indices = [i for i, score in enumerate(scores) if score > 0.0]
        ranked_indices = sorted(
            matched_indices,
            key=scores.__getitem__,
            reverse=True
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

    def _resolve_index_files(self) -> list[Path]:
        """Return the index files to search.

        One file when index_path is given (full path or just the file
        name), or every index_*.json inside data/processed when no
        file is specified.
        """
        if self.index_path is not None:
            if self.index_path.parent == Path("."):
                # Solo el nombre: index_py.json -> data/processed/index_py.json
                return [Path("data/processed") / self.index_path]
            return [self.index_path]
        index_directory = Path("data/processed")
        if not index_directory.is_dir():
            raise ValueError(
                f"Index directory does not exist: {index_directory}"
            )
        index_files = sorted(index_directory.glob("index_*.json"))
        if not index_files:
            raise ValueError(
                f"No index files found in: {index_directory}"
            )
        return index_files
