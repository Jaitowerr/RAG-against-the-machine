import json
from pathlib import Path
from .models import StudentSearchResults, RagDataset, MinimalSource


class Evaluate:
    """Compares student search results with the ground-truth dataset."""

    def __init__(
        self,
        student_search_results_path: Path,
        dataset_path: Path,
    ) -> None:
        self.student_search_results_path = student_search_results_path
        self.dataset_path = dataset_path
        self.student_results: StudentSearchResults | None = None
        self.questions: list[dict] = []
        self.k: int = 0
        self.dataset: RagDataset | None = None
        self.question_recalls: dict[str, float] = {}
        self.recall_at_k: float = 0.0

    @staticmethod
    def _load_json(file_path: Path) -> object:
        """Load a JSON file and convert read errors into ValueError."""
        try:
            return json.loads(
                file_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"JSON file cannot be read: {file_path}"
            ) from error

    def start_program(self) -> None:
        """Run every evaluation step in order."""
        self.load_results()
        self.load_dataset()
        self.validate_question_ids()
        self.compare_sources()
        self.calculate_recall_at_k()
        # Próximos pasos: validar estructuras, matching, recall, media.

    def load_results(self) -> None:
        """Load and validate the student's search results."""
        data = self._load_json(self.student_search_results_path)
        self.student_results = StudentSearchResults.model_validate(data)

    def load_dataset(self) -> None:
        """Load and validate the ground-truth dataset."""
        data = self._load_json(self.dataset_path)
        self.dataset = RagDataset.model_validate(data)


    def validate_question_ids(self) -> None:
        """Ensure both files contain the same question IDs."""
        if self.student_results is None or self.dataset is None:
            raise ValueError("Evaluation data has not been loaded.")

        student_ids = {
            result.question_id
            for result in self.student_results.search_results
        }

        dataset_ids = {
            question.question_id
            for question in self.dataset.rag_questions
            if hasattr(question, "sources")
        }

        missing_ids = dataset_ids - student_ids

        if missing_ids:
            raise ValueError(
                "Some dataset questions are missing from student results."
            )

    @staticmethod
    def _iou(
        first_a: int,
        last_a: int,
        first_b: int,
        last_b: int,
    ) -> float:
        """Return the intersection-over-union of two ranges."""
        intersection = min(last_a, last_b) - max(first_a, first_b)
        if intersection <= 0:
            return 0.0
        union = max(last_a, last_b) - min(first_a, first_b)
        return intersection / union


    IOU_THRESHOLD = 0.05

    def _is_found(
        self,
        retrieved_sources: list[MinimalSource],
        true_source: MinimalSource,
    ) -> bool:
        """Check if any retrieved source matches a true source."""
        for source in retrieved_sources:
            if source.file_path != true_source.file_path:
                continue
            overlap = self._iou(
                source.first_character_index,
                source.last_character_index,
                true_source.first_character_index,
                true_source.last_character_index,
            )
            if overlap >= self.IOU_THRESHOLD:
                return True
        return False

    def compare_sources(self) -> None:
        """Calculate recall for every answered question."""
        if self.student_results is None or self.dataset is None:
            raise ValueError("Evaluation data has not been loaded.")

        student_by_id = {
            result.question_id: result
            for result in self.student_results.search_results
        }

        for question in self.dataset.rag_questions:
            if not hasattr(question, "sources"):
                continue

            student_result = student_by_id[question.question_id]
            correct_sources = question.sources
            retrieved_sources = student_result.retrieved_sources

            found_sources = sum(
                self._is_found(retrieved_sources, source)
                for source in correct_sources
            )

            self.question_recalls[question.question_id] = (
                found_sources / len(correct_sources)
            )
    def calculate_recall_at_k(self) -> None:
        """Compute the mean recall across all evaluated questions."""
        if not self.question_recalls:
            raise ValueError("No questions have been evaluated.")

        total = sum(self.question_recalls.values())
        self.recall_at_k = total / len(self.question_recalls)
