import json
from pathlib import Path

from tqdm import tqdm

from .models import MinimalSearchResults, StudentSearchResults
from .search import Search

class SearchDataset(Search):
    """Runs the search for every question of a dataset file."""
    def __init__(
            self,
            dataset_path: Path,
            k: int,
            index_path: Path = Path("data/processed/index.json"),
        ) -> None:
            # La query va vacía: cada pregunta la sobrescribe search().
            super().__init__(query="", k=k, index_path=index_path)
            self.dataset_path = dataset_path
            self.questions: list[dict] = []


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
        return questions                                 # → construye StudentSearchResults → guarda