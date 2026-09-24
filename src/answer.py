from .search import Search
from .models import MinimalSource
from transformers import pipeline
from transformers.utils import logging as transformers_logging
import torch


class Answer(Search):
    """Answers one query using the retrieved chunks."""

    def __init__(self, query: str, k: int = 5) -> None:
        super().__init__(query, k)
        self.sources: list[MinimalSource] = []

    def retrieve_sources(self) -> list[MinimalSource]:
        """Run the inherited search and return the top-k sources."""
        self.prepare()  #carga el índice y tokeniza,
        return self.search()    #evuelve el top-k como MinimalSource

    def build_context(self) -> str:
        """Build one context string from the retrieved sources."""
        self.sources = self.retrieve_sources()

        chunks = []
        for source in self.sources:
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

    def build_prompt(self, context: str) -> str:
        """Build the prompt that will be sent to the language model."""
        return (
            "Answer the question using only the provided context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question:\n{self.query}\n\n"
            "Answer:"
        )

    def _load_generator(self) -> pipeline:
        """Load the language model once and reuse it."""
        if not hasattr(self, "_generator"):
            transformers_logging.set_verbosity_error()
            self._generator = pipeline(     #pipeline("text-generation", model=...) = "carga Qwen y dame un objeto al que le paso texto y me devuelve texto continuado, ocultándome la tokenización, el bucle de generación y la decodificación".
                "text-generation",
                model="Qwen/Qwen3-0.6B",
                device="cuda",  #mueve el modelo a la GPU (antes estaba en CPU).
                dtype=torch.bfloat16,
            )
        return self._generator

    def generate_answer(self, prompt: str) -> str:
        """Generate an answer to the query using the retrieved context."""
        generator = self._load_generator()
        output = generator(
            prompt,
            max_new_tokens=200,
            do_sample=False,
            return_full_text=False
        )
        raw_answer = output[0]["generated_text"]
        return raw_answer.split("\nAnswer:")[0].strip()
