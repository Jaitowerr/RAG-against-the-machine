# Encontrar los archivos del repo vLLM (descomprimido) que hay que indexar.
# Leer el contenido de cada archivo.
# Cortarlo en trozos (chunks) de máximo max_chunk_size caracteres.
# Guardar esos trozos en algún sitio (disco) para que search los pueda leer después.



from pathlib import Path


class Index:
    """Indexes the vLLM repository so it can be searched later."""

    SUPPORTED_SUFFIXES = {".py", ".md"}

    def __init__(
        self,
        raw_directory: Path = Path("data/raw/vllm-0.10.1"),
        index_directory: Path = Path("data/index"),
    ) -> None:
        self.raw_directory = raw_directory
        self.index_directory = index_directory

    def find_supported_files(self) -> list[Path]:
        """Return every .py and .md file inside the raw directory tree."""
        if not self.raw_directory.exists():
            raise ValueError(f"Raw directory does not exist: {self.raw_directory}")
        if not self.raw_directory.is_dir():
            raise ValueError(f"Raw path is not a directory: {self.raw_directory}")
        return [
            file_path
            for file_path in self.raw_directory.rglob("*")
            if file_path.is_file() and file_path.suffix in self.SUPPORTED_SUFFIXES
        ]
# is_dir() — hermano de is_file(). Devuelve True si esa ruta es una carpeta, False si no.
# rglob("*") — "recursive glob": recorre el árbol de carpetas desde esa ruta y va dando cada cosa que encuentra (archivos y carpetas). El "*" significa "cualquier nombre".
# is_file() — devuelve True si es un archivo normal (no una carpeta).
# suffix — la extensión del archivo con su punto: .py, .md, etc.

    def read_file(self, file_path: Path) -> str:
        """Read a single file's text content."""
        return file_path.read_text(encoding="utf-8")

    def load_documents(self) -> dict[Path, str]:
        documents = {}
        for file_path in self.find_supported_files():
            documents[file_path] = self.read_file(file_path)
        return documents

















