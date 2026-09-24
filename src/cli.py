"""Temporary CLI sandbox used to learn Python Fire."""

import sys
from pathlib import Path
from .index import Index
from .search import Search
# from .search_BM25 import SearchLibBM25 as Search

from .evaluate import Evaluate
from .search_dataset import SearchDataset
import time



class CLI:
    """Commands exposed through the command-line interface."""

    MAX_CHUNK_SIZE_LIMIT = 2000

    def index(self, max_chunk_size: int = 2000) -> None:
        """Build the index from the source code corpus.

        Args:
            max_chunk_size: Maximum number of characters allowed per chunk.
        """
        try:
            max_chunk_size = self._validate_positive_integer(
                value=max_chunk_size,
                argument_name="max_chunk_size",
            )

            if max_chunk_size > self.MAX_CHUNK_SIZE_LIMIT:
                raise ValueError(
                    f"max_chunk_size must not exceed "
                    f"{self.MAX_CHUNK_SIZE_LIMIT}."
                )
            start_time = time.perf_counter()
            print("Buscando archivos...")
            indexer = Index()
            files = indexer.find_supported_files()
            elapsed = time.perf_counter() - start_time
            if not files:
                raise ValueError("No se encontraron archivos para indexar.")
            print(f"\n\t-> Encontrados {len(files)} archivos {', '.join(sorted(indexer.supported_suffixes))} ({elapsed:.2f}s)\n")

            documents = indexer.load_documents()
            chunk_start = time.perf_counter()
            sources = indexer.chunk_documents(documents, max_chunk_size)
            chunk_elapsed = time.perf_counter() - chunk_start
            print(f"\n\t-> Troceados {len(sources)} trozos ({chunk_elapsed:.2f}s)\n")

            write_elapsed = indexer.save_index(sources, documents)
            print(
                f"\n\t\tIngestion complete! Indexed {len(sources)} chunks "
                f"under {indexer.index_directory}/ (escritura: {write_elapsed:.2f}s)\n"
            )

            total_time = time.perf_counter() - start_time
            print(f"\n\n\t\t\t\tTiempo total: {self._format_duration(total_time)}")

        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)

        # print(f"index called with max_chunk_size={max_chunk_size}")

    def search(self, query: str, k: int = 5) -> None:
        """Return the k most relevant sources for one query.

        Args:
            query: Text to search for.
            k: Number of sources to retrieve.
        """
        try:
            start_time = time.perf_counter()
            query = self._validate_query(query)
            k = self._validate_positive_integer(value=k, argument_name="k")

            searcher = Search(query, k)
            searcher.prepare()

            results = searcher.search()

            if results:
                print(f"\nResultados para {query!r}:")
                for position, source in enumerate(results, start=1):
                    print(
                        f"\t{position}. {source.file_path} "
                        f"[{source.first_character_index}:"
                        f"{source.last_character_index}]"
                    )
            else:
                print(f"\n\tNo se encontraron resultados para {query!r}.")

            total_time = time.perf_counter() - start_time
            print(
                f"\n\t\t\t\tTiempo total: "
                f"{self._format_duration(total_time)}"
            )

        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)

    # def search(self, query: str, k: int = 5) -> None:
    #     """Return the k most relevant sources for one query.

    #     Args:
    #         query: Text to search for.
    #         k: Number of sources to retrieve.
    #     """
    #     try:
    #         start_time = time.perf_counter()
    #         query = self._validate_query(query)
    #         k = self._validate_positive_integer(value=k, argument_name="k")

    #         searcher = Search(query, k)
    #         searcher.prepare()

    #         print(f"\nTokens de la consulta: {searcher.query_tokens}")
    #         print(f"\tChunks cargados: {len(searcher.entries)}")
    #         print(f"\tChunks tokenizados: {len(searcher.tokens)}")
    #         print(f"\tTérminos diferentes: {len(searcher.doc_freq)}")

    #         score = searcher._count_matching_terms(0)
    #         print(f"Coincidencias del primer chunk: {score}")



    #         for term in searcher.query_tokens:
    #             print(f"\tIDF de {term!r}: {searcher._idf(term):.4f}")

    #         print(
    #             "IDF de 'zzzpalabrainexistente': "
    #             f"{searcher._idf('zzzpalabrainexistente'):.4f}"
    #         )

    #         average_length = searcher._average_chunk_length()
    #         print(
    #             "Longitud media de los chunks: "
    #             f"{average_length:.2f} tokens"
    #         )

    #         for chunk_index in range(5):
    #             score = searcher._score_chunk(chunk_index)
    #             print(f"Puntuación del chunk {chunk_index}: {score:.4f}")

    #         results = searcher.search()

    #         print(f"Chunks cargados: {len(searcher.entries)}")
    #         print(f"Resultados para {query!r}:")
    #         for position, result in enumerate(results, start=1):
    #             print(
    #                 f"{position}. {result['file_path']} "
    #                 f"[{result['first_character_index']}:"
    #                 f"{result['last_character_index']}]"
    #             )

    #         total_time = time.perf_counter() - start_time
    #         print(f"\n\n\t\t\t\tTiempo total: {self._format_duration(total_time)}")

    #     except ValueError as error:
    #         print(f"Error: {error}", file=sys.stderr)
    #         sys.exit(1)

    #     print(f"\t\t\t\tsearch called with query={query!r} and k={k}")

    def search_dataset(
        self,
        dataset_path: str,
        k: int,
        save_directory: str = "data/output"
    ) -> None:
        """Search every question in a dataset.

        Args:
            dataset_path: Path to the input dataset JSON file.
            k: Number of sources to retrieve per question.
            save_directory: Directory where results will be written.
        """
        try:
            start_time = time.perf_counter()
            dataset_file = self._validate_existing_file(
                path_string=dataset_path,
                argument_name="dataset_path",
            )
            k = self._validate_positive_integer(value=k, argument_name="k")
            output_directory = self._validate_output_directory(
                directory_string=save_directory,
                input_file=dataset_file,
            )

            searcher = SearchDataset(dataset_file, k)
            questions = searcher.load_dataset()
            print(f"\t-> Cargadas {len(questions)} preguntas de {dataset_file.name}\n")

            results = searcher.search_all()
            print(f"\n\t-> Buscadas {len(results)} preguntas")

            output_path = searcher.save_results(results, output_directory)
            print(f"\n\t-> Resultados guardados en {output_path}")

            total_time = time.perf_counter() - start_time
            print(
                f"\n\t\t\t\tTiempo total: "
                f"{self._format_duration(total_time)}"
            )

        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)


    def answer(self, query: str, k: int = 5) -> None:
        """Answer one query using the retrieved sources.

        Args:
            query: Question to answer.
            k: Number of sources to use as context.
        """
        try:
            start_time = time.perf_counter()
            query = self._validate_query(query)
            k = self._validate_positive_integer(value=k, argument_name="k")
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)

        print(f"answer called with query={query!r} and k={k}")

    def answer_dataset(
        self,
        student_search_results_path: str,
        save_directory: str,
    ) -> None:
        """Generate answers from a search-results JSON file.

        Args:
            student_search_results_path: Path to search results JSON.
            save_directory: Directory where answers will be written.
        """
        try:
            start_time = time.perf_counter()
            search_results_file = self._validate_existing_file(
                path_string=student_search_results_path,
                argument_name="student_search_results_path",
            )
            output_directory = self._validate_output_directory(save_directory)
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)

        print(
            "answer_dataset called with "
            f"student_search_results_path={search_results_file}, "
            f"save_directory={output_directory}"
        )

    def evaluate(
        self,
        student_search_results_path: str,
        dataset_path: str,
    ) -> None:
        """Evaluate search results against a ground-truth dataset.

        Args:
            student_search_results_path: Path to student search results JSON.
            dataset_path: Path to the ground-truth dataset JSON.
        """
        try:
            start_time = time.perf_counter()
            search_results_file = self._validate_existing_file(
                path_string=student_search_results_path,
                argument_name="student_search_results_path",
            )
            dataset_file = self._validate_existing_file(
                path_string=dataset_path,
                argument_name="dataset_path",
            )

            evaluator = Evaluate(search_results_file, dataset_file)
            evaluator.start_program()
            
            # print("\t-> Resultados y dataset cargados correctamente\n")
            print(
                f"\n\t-> Recall@k: "
                f"{evaluator.recall_at_k:.4f} "
                f"(k={evaluator.student_results.k}, "
                f"{len(evaluator.question_recalls)} preguntas)\n"
            )

            total_time = time.perf_counter() - start_time
            print(
                f"\n\t\t\t\tTiempo total: "
                f"{self._format_duration(total_time)}"
            )

        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)


    # def evaluate(
    #     self,
    #     student_search_results_path: str,
    #     dataset_path: str,
    # ) -> None:
    #     """Evaluate search results against a ground-truth dataset.

    #     Args:
    #         student_search_results_path: Path to student search results JSON.
    #         dataset_path: Path to the ground-truth dataset JSON.
    #     """
    #     try:
    #         start_time = time.perf_counter()
    #         search_results_file = self._validate_existing_file(
    #             path_string=student_search_results_path,
    #             argument_name="student_search_results_path",
    #         )
    #         dataset_file = self._validate_existing_file(
    #             path_string=dataset_path,
    #             argument_name="dataset_path",
    #         )
    #     except ValueError as error:
    #         print(f"Error: {error}", file=sys.stderr)
    #         sys.exit(1)

    #     print(
    #         "evaluate called with "
    #         f"student_search_results_path={search_results_file}, "
    #         f"dataset_path={dataset_file}"
    #     )

    @staticmethod
    def _validate_query(query: str) -> str:
        """Ensure that a query contains meaningful text."""
        if not isinstance(query, str):
            raise ValueError("query must be a string.")

        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("query must not be empty.")

        return cleaned_query

    @staticmethod
    def _validate_positive_integer(value: object, argument_name: str) -> int:
        """Convert a value to a strictly positive integer."""
        if isinstance(value, bool):
            raise ValueError(f"{argument_name} must be an integer.")
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"{argument_name} must be an integer.")
        try:
            integer_value = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{argument_name} must be a positive integer."
            ) from error

        if integer_value <= 0:
            raise ValueError(
                f"{argument_name} must be greater than 0."
            )

        return integer_value

    @staticmethod
    def _validate_existing_file(
        path_string: str,
        argument_name: str,
    ) -> Path:
        """Ensure that a path exists, is a readable file and is a JSON file."""
        file_path = Path(path_string)

        if not file_path.exists():
            raise ValueError(
                f"{argument_name} does not exist: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"{argument_name} must be a file: {file_path}"
            )

        if file_path.suffix.lower() != ".json":
            raise ValueError(
                f"{argument_name} must point to a JSON file: {file_path}"
            )

        try:
            with file_path.open("r", encoding="utf-8"):
                pass
        except OSError as error:
            raise ValueError(
                f"{argument_name} cannot be read: {file_path}"
            ) from error

        return file_path

    @staticmethod
    def _validate_output_directory(
        directory_string: str,
        input_file: Path | None = None
    ) -> Path:
        """Create an output directory when possible and verify write access."""
        output_directory = Path(directory_string)

        if output_directory.exists() and not output_directory.is_dir():
            raise ValueError(
                f"save_directory must be a directory: {output_directory}"
            )
        if output_directory.suffix:
            raise ValueError(
                f"save_directory must be a directory, not a file: "
                f"{output_directory}"
            )
        if input_file is not None:
            if output_directory.resolve() == input_file.parent.resolve():
                raise ValueError(
                    f"save_directory must be different from the input "
                    f"file directory: {output_directory}"
                )

        try:
            output_directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ValueError(
                f"save_directory cannot be created: {output_directory}"
            ) from error

        return output_directory

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format a duration in seconds as HH:MM:SS.microseconds."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        microseconds = int((seconds - int(seconds)) * 1_000_000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{microseconds:06d}"

# make run
# make run -- --help
# make run -- index --max_chunk_size 500
# make run -- index --help
# make run -- search
# make run -- search "hello world"
# make run -- search "hello world" --k 3
# make run -- buscar_typo "hello"
# make run -- index --max_chunk_size abc
