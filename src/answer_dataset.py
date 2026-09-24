from pathlib import Path

from pydantic import ValidationError

from .css import StyledBar
from .models import (
    MinimalAnswer,
    MinimalSearchResults,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
)
from .answer import Answer


class AnswerDataset(Answer):
    """Generates an answer for every question of a search-results file."""

    def __init__(
        self,
        results_path: Path,
        save_directory: Path,
    ) -> None:
        super().__init__(query="", k=1)
        self.results_path = results_path
        self.save_directory = save_directory

    def open_search_result(self) -> StudentSearchResults:
        """Read the search-results JSON and validate its structure."""
        try:
            data = self.results_path.read_text(encoding="utf-8")
            return StudentSearchResults.model_validate_json(data)
        except (OSError, ValidationError) as error:
            raise ValueError(
                f"Invalid search-results file: {self.results_path}"
            ) from error

    def _build_context(self, result: MinimalSearchResults) -> str:
        """Build the prompt context for one search result."""
        self.sources = result.retrieved_sources
        chunks = [self._chunk_text(source) for source in self.sources]
        return "\n\n".join(chunks)

    def answer_all(
        self,
        results: StudentSearchResults,
    ) -> StudentSearchResultsAndAnswer:
        """Prepare the index once and answer all results in GPU batches."""
        self.k = results.k
        self.prepare()

        contexts: list[str] = []
        prompts: list[str] = []
        for result in results.search_results:
            self.query = result.question
            context = self._build_context(result)
            contexts.append(context)
            if context.strip():
                prompts.append(self.build_prompt(context))

        generated: list[str] = []
        lotes_por_prompt = 10
        batches = [
            prompts[start:start + lotes_por_prompt]
            for start in range(0, len(prompts), lotes_por_prompt)  #enviamos los 8 primeros prompt
        ]
        for batch in StyledBar(batches, desc="Respondiendo preguntas"):
            generated.extend(self.generate_answers(batch))

        answers: list[MinimalAnswer] = []
        fresh_answers = iter(generated)
        for result, context in zip(results.search_results, contexts):
            answers.append(
                MinimalAnswer(
                    question_id=result.question_id,
                    question=result.question,
                    retrieved_sources=result.retrieved_sources,
                    answer=next(fresh_answers) if context.strip() else "",
                )
            )

        return StudentSearchResultsAndAnswer(
            search_results=answers,
            k=self.k,
        )

    def save_answers(
        self,
        answers: StudentSearchResultsAndAnswer,
    ) -> Path:
        """Save the answers as a JSON file, asking before overwriting."""
        output_path = self.save_directory / self.results_path.name

        if output_path.exists():
            reply = input(
                f"{output_path} ya existe. ¿Sobrescribir? [y/N] "
            )
            if reply.strip().lower() not in {"y", "yes"}:
                raise ValueError(
                    f"Output file already exists: {output_path}"
                )

        try:
            output_path.write_text(
                answers.model_dump_json(indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            raise ValueError(
                f"Answers file cannot be written: {output_path}"
            ) from error

        return output_path
