# Encontrar los archivos del repo vLLM (descomprimido) que hay que indexar.
# Leer el contenido de cada archivo.
# Cortarlo en trozos (chunks) de máximo max_chunk_size caracteres.
# Guardar esos trozos en algún sitio (disco) para que search los pueda leer después.



from pathlib import Path
from tqdm import tqdm
from .chunker import Chunker
from .models import MinimalSource
import json
import time


class Index:
    """Indexes the vLLM repository so it can be searched later."""


    def __init__(
        self,
        raw_directory: Path = Path("data/raw/vllm-0.10.1"),
        index_directory: Path = Path("data/processed"),
        supported_suffixes: set[str] = {".py", ".md"}
    ) -> None:
        self.raw_directory = raw_directory
        self.index_directory = index_directory
        self.supported_suffixes = supported_suffixes

    def find_supported_files(self) -> list[Path]:
        """Return every .py and .md file inside the raw directory tree."""
        if not self.raw_directory.exists():
            raise ValueError(f"Raw directory does not exist: {self.raw_directory}")
        if not self.raw_directory.is_dir():
            raise ValueError(f"Raw path is not a directory: {self.raw_directory}")
        return [
            file_path
            for file_path in self.raw_directory.rglob("*")
            if file_path.is_file() and file_path.suffix in self.supported_suffixes
        ]
# is_dir() — hermano de is_file(). Devuelve True si esa ruta es una carpeta, False si no.
# rglob("*") — "recursive glob": recorre el árbol de carpetas desde esa ruta y va dando cada cosa que encuentra (archivos y carpetas). El "*" significa "cualquier nombre".
# is_file() — devuelve True si es un archivo normal (no una carpeta).
# suffix — la extensión del archivo con su punto: .py, .md, etc.

    def read_file(self, file_path: Path) -> str:
        """Read a single file's text content."""
        return file_path.read_text(encoding="utf-8")

    def load_documents(self) -> dict[Path, str]:
        """Read every supported file into a {path: content} mapping."""
        documents = {}
        for file_path in tqdm(self.find_supported_files(), desc="Leyendo archivos"):
            documents[file_path] = self.read_file(file_path)
        return documents

    def chunk_documents(
        self,
        documents: dict[Path, str],
        max_chunk_size: int,
    ) -> list[MinimalSource]:
        """Split every document into chunks and return them as sources."""
        chunker = Chunker(self.supported_suffixes)
        sources = []
        for file_path, content in tqdm(documents.items(), desc="Troceando documentos"):
            for start, end in chunker.split_text(content, max_chunk_size, file_path.suffix):
                sources.append(
                    MinimalSource(
                        file_path=str(file_path),
                        first_character_index=start,
                        last_character_index=end,
                    )
                )
        return sources

    def save_index(
        self,
        sources: list[MinimalSource],
        documents: dict[Path, str],
    ) -> float:
        """Persist the chunked index to disk as JSON.

        Args:
            sources: Chunks to persist.
            documents: Original file contents keyed by path.

        Returns:
            Seconds spent serializing and writing the JSON file.
        """
        self.index_directory.mkdir(parents=True, exist_ok=True)
        entries = []
        # for source in sources:
        for source in tqdm(sources, desc="Creando índice", unit="chunk"):
            content = documents[Path(source.file_path)]
            text = content[source.first_character_index:source.last_character_index]
            entries.append(
                {
                    "file_path": source.file_path,
                    "first_character_index": source.first_character_index,
                    "last_character_index": source.last_character_index,
                    "text": text,
                }
            )
        write_start = time.perf_counter()
        output_path = self.index_directory / "index.json"
        output_path.write_text(
            json.dumps(entries, indent=2),
            encoding="utf-8",
        )
        return time.perf_counter() - write_start

# MinimalSource: "corta aquí, desde A hasta B".
# json.dumps(entries, indent=2) — convierte la lista a JSON con sangría (legible para depurar;
# output_path.write_text(..., encoding="utf-8") — lo escribe en data/processed/index.json.










