import json
from pathlib import Path

from .css import StyledBar

from .models import MinimalSearchResults, StudentSearchResults
from .search import Search
# from .search_BM25 import SearchLibBM25 as Search


class SearchDataset(Search):
    """Runs the search for every question of a dataset file."""

    def __init__(
        self,
        dataset_path: Path,
        k: int,
    ) -> None:
        resolved_index = self._resolve_index_path_from_dataset(dataset_path)
        # La query va vacía: cada pregunta la sobrescribe search().
        super().__init__(query="", k=k, index_path=resolved_index)
        self.dataset_path = dataset_path
        self.questions: list[dict] = []
        self.questions: list[dict] = []

    @staticmethod
    def _resolve_index_path_from_dataset(dataset_path: Path) -> Path | None:
        """Derive the index file from the dataset name, or None for all.

        dataset_code_public.json -> index_py.json,
        dataset_docs_public.json -> index_md.json,
        dataset_txt_public.json  -> index_txt.json.
        Returns None when the file does not exist or the name gives no clue.
        """
        suffix_map = {"code": "py", "docs": "md"}
        parts = dataset_path.stem.split("_")
        if len(parts) < 2:
            return None
        token = parts[1].lower()
        extension = suffix_map.get(token, token)
        index_path = Path("data/processed") / f"index_{extension}.json"
        if index_path.is_file():
            return index_path
        return None

    def load_dataset(self) -> list[dict]:
        """Read the dataset JSON and extract its questions."""
        try:
            data = json.loads(
                self.dataset_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"Dataset file cannot be read: {self.dataset_path}"
            ) from error

        if not isinstance(data, dict) or "rag_questions" not in data:
            raise ValueError(
                f"Dataset file is malformed: {self.dataset_path}"
            )

        questions = data["rag_questions"]
        if not isinstance(questions, list) or not questions:
            raise ValueError(
                f"Dataset has no questions: {self.dataset_path}"
            )

        for position, question in enumerate(questions):
            if not isinstance(question, dict):
                raise ValueError(
                    f"Dataset question {position} is not an object."
                )
            if not question.get("question_id"):
                raise ValueError(
                    f"Dataset question {position} has no 'question_id'."
                )
            if not str(question.get("question", "")).strip():
                raise ValueError(
                    f"Dataset question {position} has no 'question'."
                )

        self.questions = questions
        # → construye StudentSearchResults → guarda
        return questions

    def search_all(self) -> list[MinimalSearchResults]:
        """Prepare the index once and search every question."""
        self.prepare()

        fallback_searcher: Search | None = None
        results: list[MinimalSearchResults] = []
        for question in StyledBar(self.questions, desc="Buscando por preguntas"):
            query = str(question["question"])
            retrieved = self.search(query)

            # Fallback: con índice específico y 0 resultados, busca en todos.
            if not retrieved and self.index_path is not None:
                if fallback_searcher is None:
                    fallback_searcher = Search("", self.k)
                    fallback_searcher.prepare()
                retrieved = fallback_searcher.search(query)

            results.append(
                MinimalSearchResults(
                    question_id=str(question["question_id"]),
                    question=query,
                    retrieved_sources=retrieved,
                )
            )
        return results

    # def search_all(self) -> list[MinimalSearchResults]:
    #     """Prepare the index once and search every question."""
    #     self.prepare()

    #     results: list[MinimalSearchResults] = []
    #     for question in StyledBar(self.questions, desc="Buscando por preguntas"):
    #         query = str(question["question"])
    #         results.append(
    #             MinimalSearchResults(
    #                 question_id=str(question["question_id"]),
    #                 question=query,
    #                 retrieved_sources=self.search(query),
    #             )
    #         )
    #     return results

    def save_results(
        self,
        results: list[MinimalSearchResults],
        output_directory: Path,
    ) -> Path:
        """Wrap the results in a StudentSearchResults and save it as JSON."""
        output = StudentSearchResults(
            search_results=results,
            k=self.k,
        )

        output_path = output_directory / self.dataset_path.name

        if output_path.exists():
            reply = input(
                f"{output_path} ya existe. ¿Sobrescribir? [y/N] "
            )
            if reply.strip().lower() not in {"y", "yes"}:
                raise ValueError(
                    f"Results file already exists: {output_path}"
                )

        try:
            output_path.write_text(
                output.model_dump_json(indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            raise ValueError(
                f"Results file cannot be written: {output_path}"
            ) from error

        return output_path

    # def save_results(
    #     self,
    #     results: list[MinimalSearchResults],
    #     output_directory: Path,
    # ) -> Path:
    #     """Wrap the results in a StudentSearchResults and save it as JSON."""
    #     output = StudentSearchResults(
    #         search_results=results,
    #         k=self.k,
    #     )

    #     output_path = output_directory / self.dataset_path.name

    #     try:
    #         output_path.write_text(
    #             output.model_dump_json(indent=2),
    #             encoding="utf-8",
    #         )
    #     except OSError as error:
    #         raise ValueError(
    #             f"Results file cannot be written: {output_path}"
    #         ) from error

    #     return output_path
