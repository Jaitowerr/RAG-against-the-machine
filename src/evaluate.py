import json
from pathlib import Path


class Evaluate:
    """Compares student search results with the ground-truth dataset."""

    def __init__(
        self,
        student_search_results_path: Path,
        dataset_path: Path,
    ) -> None:
        self.student_search_results_path = student_search_results_path
        self.dataset_path = dataset_path

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
        # Próximos pasos: validar estructuras, matching, recall, media.

    def load_results(self) -> None:
        """Read the student search results JSON."""
        self._load_json(self.student_search_results_path)

    def load_dataset(self) -> None:
        """Read the ground-truth dataset JSON."""
        self._load_json(self.dataset_path)