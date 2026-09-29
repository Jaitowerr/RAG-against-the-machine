_This project was created as part of the 42 curriculum by aitorres._

<div align="center">

# RAG against the machine

**Retrieval-Augmented Generation**

_42 Madrid - Fundación Telefónica_

![Python 3.10](https://img.shields.io/badge/Python-3.10-blue.svg) ![uv](https://img.shields.io/badge/Package_Manager-uv-orange.svg) ![Qwen3-0.6B](https://img.shields.io/badge/LLM-Qwen--3--0.6B-green.svg) ![Mypy Strict](https://img.shields.io/badge/Lint-Strict-red.svg)

</div>

---

A local retrieval-augmented generation (RAG) system that answers questions about the **vLLM 0.10.1** source code. The system retrieves relevant chunks using a manually implemented BM25 search engine and provides them to **Qwen/Qwen3-0.6B**, which generates an answer based exclusively on the retrieved evidence.

## Contents

1. [Description](#description)
2. [Instructions](#instructions)
3. [System architecture](#system-architecture)
4. [Chunking strategy](#chunking-strategy)
5. [Retrieval method](#retrieval-method)
6. [Generated files](#generated-files)
7. [Data models](#data-models)
8. [Command reference](#command-reference)
9. [Performance analysis](#performance-analysis)
10. [Design decisions](#design-decisions)
11. [Difficulties](#difficulties)
12. [Usage example](#usage-example)
13. [Bonus](#bonus)
14. [Known limitations](#known-limitations)
15. [Resources and AI usage](#resources-and-ai-usage)

<br>

## Description

The project implements the complete RAG pipeline over a real codebase:

1. **Indexing:** reads `.py` and `.md` files, splits them into chunks, and stores the indexes.
2. **Retrieval:** receives a question and returns the most relevant source-code ranges.
3. **Augmentation:** extracts the text from the retrieved chunks and builds a context.
4. **Generation:** sends the context and the question to Qwen/Qwen3-0.6B.
5. **Evaluation:** compares the retrieved sources with the reference by using Recall@k.

The system does not train or fine-tune any model. It runs locally and does not require API keys.

```text
vLLM repository (.py and .md)
        |
        | make run -- index
        v
Chunks and JSON indexes
        |
        | make run -- search_dataset
        v
BM25 top-k retrieval
        |
        | make run -- answer / answer_dataset
        v
Context + prompt + Qwen/Qwen3-0.6B
        |
        | make run -- evaluate
        v
Recall@k evaluation
```

The common information unit is `MinimalSource`, which contains `file_path`, `first_character_index`, and `last_character_index`. This format is used throughout the retrieval and evaluation pipeline.

<br>

## Instructions

### Requirements

* Python 3.10 or newer.
* `uv` for managing the environment and dependencies.
* Several gigabytes may be required for machine-learning dependencies and model weights.
* A GPU is optional. CUDA is used when available; otherwise, the system runs on the CPU.

### Installation and execution

The project is designed to run through the `Makefile`. The `make run` rule first synchronizes the environment with `uv sync`, runs the requested command, and then cleans temporary Python caches.

```bash
make install
make run -- index
make run -- search '"How is the KV cache managed?" --k 5'
make run -- answer '"What is the purpose of the scheduler?" --k 5'
```

`make install` synchronizes the environment and dependencies. During normal use, `make run -- <command>` is sufficient because it synchronizes the environment again before running the command.

The vLLM repository must be placed at:

```text
data/raw/vllm-0.10.1/
```

Datasets must be placed at:

```text
data/datasets/UnansweredQuestions/
data/datasets/AnsweredQuestions/
```

The corpus, datasets, model weights, generated indexes, caches, and output files must not be included in the repository.

### Makefile rules

| Rule | Description |
| --- | --- |
| `make install` | Synchronizes dependencies with `uv sync`. |
| `make run -- <command> [options]` | Synchronizes the environment and runs `uv run python -m src <command>`. |
| `make debug` | Starts the main module through `pdb`. |
| `make clean` | Removes temporary Python and type-checking caches. |
| `make lint` | Runs `flake8` and the non-strict `mypy` configuration. |
| `make lint-strict` | Runs `flake8` and `mypy --strict`. |

### Repository structure

```text
.
├── src/
│   ├── __main__.py
│   ├── cli.py
│   ├── index.py
│   ├── chunker.py
│   ├── search.py
│   ├── search_dataset.py
│   ├── answer.py
│   ├── answer_dataset.py
│   ├── evaluate.py
│   ├── models.py
│   ├── api.py
│   └── css.py
├── data/
│   ├── raw/vllm-0.10.1/
│   ├── processed/
│   ├── datasets/
│   └── output/
├── pyproject.toml
├── uv.lock
├── Makefile
├── .gitignore
└── README.md
```

<br>

## System architecture

The system is divided into layers with separate responsibilities:

| Module | Responsibility |
| --- | --- |
| `__main__.py` | Entry point that exposes the `CLI` class through Python Fire. |
| `cli.py` | Validates arguments, coordinates operations, measures execution times, and displays errors. |
| `index.py` | Traverses the corpus, coordinates chunking, and writes one JSON index per extension. |
| `chunker.py` | Splits files according to their extension and the configured maximum size. |
| `search.py` | Implements tokenization, BM25 scoring, index preparation, and caching. |
| `search_dataset.py` | Runs retrieval for every question in a dataset. |
| `answer.py` | Retrieves sources, builds the context and prompt, and calls Qwen. |
| `answer_dataset.py` | Generates answers for a complete search-results file in batches. |
| `evaluate.py` | Compares retrieved ranges with reference sources and calculates Recall@k. |
| `models.py` | Defines the Pydantic models used at JSON boundaries. |
| `api.py` | Provides the optional local FastAPI interface. |
| `css.py` | Provides a common, styled `tqdm` progress bar. |

For an individual `answer` request, the flow is:

```text
Question and k
      |
      v
Retrieve MinimalSource objects with BM25
      |
      v
Read the corresponding ranges from the original files
      |
      v
Build the context and prompt
      |
      v
Generate with Qwen/Qwen3-0.6B
      |
      v
Return an AnsweredQuestion
```

The model is not involved during indexing or retrieval. It is called only after the context has been built.

<br>

## Chunking strategy

The default maximum size is **2,000 characters**, which is also the maximum accepted by the assignment. It can be configured with `--max_chunk_size`, but values above 2,000 are rejected.

`Chunker` uses a strategy based on the file extension:

* `.py` files use the Python strategy.
* `.md` files use the Markdown strategy.
* Unknown extensions use a generic character-based fallback.

### Python and Markdown files

Supported formats are first split using blank-line separators. The separator recognizes several blank lines and lines containing spaces or tabs:

```text
\\n(?:[ \\t]*\\n)+
```

The separatorizer chooses the last suitable separator within the allowed window. If no appropriate blank-line separator exists, it uses the last single newline and, as a final fallback, cuts at the maximum character limit.

This approach attempts to preserve natural boundaries between functions, classes, paragraphs, and sections. However, a function or paragraph that exceeds the limit may be split to guarantee that no chunk exceeds 2,000 characters.

### Overlap

Each sufficiently large chunk repeats up to 20% of the previous chunk, with an absolute maximum of 60 characters. Chunks shorter than 120 characters receive no overlap. This reduces the risk of losing information at a boundary.

Chunks are initially represented as `(start, end)` ranges. The original file remains the source of truth; the text is copied into the JSON index when it is saved.

## Retrieval method

The assignment requires TF-IDF or BM25. This project uses **BM25**, implemented directly in `search.py` without using the `rank-bm25` library in the official flow. `search_BM25.py` is an optional comparison experiment that uses the external library.

### Why BM25 instead of TF-IDF?

BM25 was selected because it addresses two common problems in code retrieval:

* **Term-frequency saturation:** repeating an identifier many times should not increase its relevance indefinitely in a linear way.
* **Length normalization:** long chunks should not rank highly only because they contain more tokens.

The implementation uses the following formulas:

$$
IDF(t) = \log\left(1 + \frac{N - n(t) + 0.5}{n(t) + 0.5}\right)
$$

$$
BM25(D, Q) = \sum_{t \in Q} IDF(t) \cdot \frac{f(t,D)(k_1+1)}{f(t,D)+k_1\left(1-b+b\frac{|D|}{avgdl}\right)}
$$

The parameters used are:

```text
k1 = 1.2
b  = 0.45
```

The same tokenizer is applied to questions and chunks. It converts text to lowercase, splits camelCase boundaries, and extracts alphanumeric tokens. For example, `SamplingParams` can match through the `sampling` and `params` tokens.

The prepared search state contains:

* indexed entries;
* tokens for every chunk;
* term frequencies for every chunk;
* document frequency for every term;
* query tokens;
* average chunk length.

The average length is calculated once during `prepare()`, instead of once for every scored chunk. Dataset searches prepare the index once and reuse it for every question.

Results are sorted by descending BM25 score. Only chunks with a positive score are returned. Python's stable sorting preserves index order when scores are tied, so results are deterministic for the same query and index.

For code datasets, `index_py.json` is used, and for documentation datasets, `index_md.json` is used when those indexes exist. If the selected index returns no results, a fallback searches all available indexes.

## Generated files

### JSON indexes

```text
data/processed/index_py.json
data/processed/index_md.json
```

Each entry stores the source path, character range, and extracted text:

```json
{
  "file_path": "data/raw/vllm-0.10.1/vllm/sampling_params.py",
  "first_character_index": 3571,
  "last_character_index": 5547,
  "text": "..."
}
```

JSON is used because it is readable, easy to inspect, and compatible with the evaluation flow.

### BM25 preparation cache

```text
data/processed/cache/search_cache_py.pkl
data/processed/cache/search_cache_md.pkl
data/processed/cache/search_cache_all.pkl
```

The cache stores the prepared Python state: tokens, term frequencies, document frequencies, and average length. It caches the prepared index, not individual query results.

The cache stores a fingerprint based on the index path, file size, and modification time. If the index changes, the cache is ignored and recalculated.

### Incremental-indexing manifest

```text
data/processed/manifest_index.json
```

The manifest stores the configured chunk size and a SHA-256 content fingerprint for every indexed file. SHA-256 is a one-way hash, not encryption or a secret-key mechanism. It is used only to detect changes.

Files are classified as unchanged, modified, new, or deleted. Unchanged chunks are reused, while new or modified files are chunked again. Changing the maximum chunk size triggers a complete rebuild.

## Data models

The main Pydantic models are:

| Model | Purpose |
| --- | --- |
| `MinimalSource` | Source path and character range. |
| `UnansweredQuestion` | Question with an identifier. |
| `AnsweredQuestion` | Question, sources, and generated answer. |
| `RagDataset` | Dataset containing `rag_questions`. |
| `MinimalSearchResults` | Question and retrieved sources. |
| `MinimalAnswer` | Search results plus an answer. |
| `StudentSearchResults` | Student search output plus `k`. |
| `StudentSearchResultsAndAnswer` | Answer output plus `k`. |

Datasets, search results, generated answers, and API requests are validated with Pydantic. Internal indexes are loaded as JSON entries because they contain the serialized chunk data used by the search engine.

## Command reference

All commands must be run through the Makefile:

```text
make run -- <command> [options]
```

| Command | Purpose |
| --- | --- |
| `index` | Build or update source-code indexes. |
| `search` | Print the top-k chunks for a query. |
| `search_dataset` | Search every question in a dataset and save JSON results. |
| `answer` | Retrieve sources and generate an individual answer. |
| `answer_dataset` | Generate answers from an existing search-results JSON file. |
| `evaluate` | Calculate Recall@k against a reference dataset. |
| `serve` | Start the optional local HTTP API. |

### `index`

```bash
make run -- index
make run -- index --max_chunk_size 1500
```

Traverses `data/raw/vllm-0.10.1/`, indexes `.py` and `.md` files, and writes the results to `data/processed/`. If neither the corpus nor the configuration has changed, later executions reuse the existing index.

### `search`

```bash
make run -- search '"How is the KV cache managed?" --k 5'
```

This command is intended for interactive inspection and prints paths and character ranges to the terminal. It does not create a dataset-results file.

### `search_dataset`

```bash
make run -- search_dataset \\
  --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \\
  --k 5 \\
  --save_directory data/output/search_results/UnansweredQuestions
```

Saves a `StudentSearchResults` JSON file with the same name as the input dataset. The output directory must be different from the input dataset directory. If the file already exists, the program asks for confirmation before overwriting it.

### `answer`

```bash
make run -- 'answer "What is the purpose of the scheduler?" --k 5'
```

Prints an `AnsweredQuestion` containing the question, retrieved sources, and generated answer. Qwen is loaded only when relevant context exists.

### `answer_dataset`

```bash
make run -- answer_dataset \\
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \\
  --save_directory data/output/search_results_and_answer/UnansweredQuestions
```

It does not perform retrieval again. It reads the existing `StudentSearchResults`, rebuilds contexts from the stored sources, and generates answers in batches. If the output file already exists, the program asks for confirmation before overwriting it.

### `evaluate`

```bash
make run -- evaluate \\
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \\
  --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json
```

For a retrieved source to be considered correct, the path must match exactly and the character ranges must have an Intersection over Union of at least 0.05.

$$
IoU(A,B) = \frac{|A \cap B|}{|A \cup B|}
$$

The recall for each question is the proportion of reference sources that were retrieved. Global Recall@k is the mean of the individual recalls.

## Performance analysis

The following values were measured with `k = 5` and the official moulinette on September 24, 2026:

| Dataset | Required Recall@5 | Measured Recall@5 | Status |
| --- | --- | --- | --- |
| `docs_public` | 0.80 | 0.8600 | Passed |
| `docs_private` | 0.80 | 0.8300 | Passed |
| `code_public` | 0.50 | 0.6465 | Passed |
| `code_private` | 0.50 | 0.5200 | Passed |

The result closest to the minimum is `code_private`, with 0.5200 compared with the required 0.50.

The project also aims to meet the assignment's execution limits:

* complete indexing in less than five minutes;
* process 200 questions in less than 90 seconds.

In one execution, dataset processing reached approximately 33 questions per second: 99 questions in approximately 3.5 seconds. Exact times depend on the machine and environment.

In the first implementation, average chunk length was recalculated while each chunk was being scored. This created unnecessary quadratic cost. Moving the calculation to `prepare()` reduced measured preparation from approximately 5.5 seconds per query to approximately 0.6 seconds, while preserving the same ranking logic. The preparation cache avoids repeating this work in later executions.

## Design decisions

* **BM25 implemented directly:** provides transparent control over scoring, tokenization, caching, and deterministic ordering.
* **JSON indexes:** readable, easy to debug, and compatible with the required format.
* **Pickle for prepared BM25 state:** efficiently preserves Python structures such as `Counter`. It is used only for internal cache data.
* **SHA-256 manifest:** detects content changes for incremental indexing. It is a hash, not encryption.
* **Separate indexes by extension:** allow code and documentation to be searched independently, reducing irrelevant matches.
* **Pydantic at data boundaries:** validates datasets, result files, answers, and API requests.
* **Inheritance:** `SearchDataset` and `Answer` reuse the common search implementation instead of duplicating BM25 logic.
* **Deterministic generation:** Qwen uses `do_sample=False`, and retrieval keeps stable ordering for ties.
* **Local generation:** the system uses `Qwen/Qwen3-0.6B` through `transformers` and does not use API keys.
* **Makefile-based execution:** `make run` synchronizes dependencies, runs the command with `uv`, and performs the subsequent cleanup.

## Difficulties

| Difficulty | Solution |
| --- | --- |
| Recalculating average length for every scored chunk | Calculate it once in `prepare()`. |
| Irregular blank-line separators | Use a regular expression accepting several blank lines and spaces. |
| Reusing chunks during incremental indexing | Store SHA-256 fingerprints in `manifest_index.json`. |
| Distinguishing equivalent paths such as `data/output` and `./data/output` | Compare resolved paths. |
| Python booleans behaving like integers | Reject them before validating integers. |
| Decimals being silently truncated by `int()` | Reject non-integer floats before conversion. |
| Limited space on 42 Madrid computers | Use `set-local.sh` to direct environments and caches to `sgoinfre`. |

## Usage example

Complete flow:

```bash
make install
make run -- index

for d in docs_public docs_private code_public code_private; do
  make run -- search_dataset \\
    --dataset_path data/datasets/UnansweredQuestions/dataset_$d.json \\
    --k 5 \\
    --save_directory data/output/search_results/UnansweredQuestions
done

make run -- evaluate \\
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \\
  --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json

make run -- answer_dataset \\
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \\
  --save_directory data/output/search_results_and_answer/UnansweredQuestions

make run -- answer "What is the purpose of the scheduler?" --k 5
make run -- serve
```

An individual answer has this general structure:

```json
{
  "question": "What is the purpose of the scheduler?",
  "sources": [
    {
      "file_path": "data/raw/vllm-0.10.1/vllm/core/scheduler.py",
      "first_character_index": 1000,
      "last_character_index": 1800
    }
  ],
  "answer": "Answer generated from the retrieved context."
}
```

## Bonus

| Bonus | Status | Description |
| --- | --- | --- |
| Incremental indexing | Implemented | SHA-256 manifest and reuse of unchanged file chunks. |
| Caching | Implemented | Tokenization and BM25-statistics cache; individual queries are not cached. |
| Local HTTP API | Implemented | FastAPI endpoints for search and answers. |
| Semantic embeddings | Not implemented | — |
| Hybrid retrieval | Not implemented | — |

The three implemented bonuses follow the same idea: do not repeat work that has already been done. Incremental indexing avoids reindexing unchanged files, caching avoids preparing an already prepared index again, and the API reuses the same classes as the command line instead of duplicating the logic.

### Incremental indexing

The question it solves is: why split all vLLM files again if only one has changed? `Index.update_index()` in `index.py` avoids this as follows:

1. It computes the SHA-256 of each compatible file's content (`_file_fingerprint` reads the bytes and hashes them).
2. It loads the previous execution's `manifest_index.json`, which stores those fingerprints and the `max_chunk_size` used.
3. It compares both lists in `_classify_files` and classifies every file as unchanged, modified, new, or deleted. If `max_chunk_size` changed, all files are marked for a complete rebuild.
4. If there are no new, modified, or deleted files, it reports that the index is up to date and stops without changing anything.
5. Unchanged files contribute their existing chunks, taken from the existing JSON indexes and filtered by path.
6. Only new and modified files are read and chunked again with `Chunker`, and their chunks are added to the preserved chunks.
7. The indexes are rewritten by extension with the combined result, and the manifest is saved with the current fingerprints so that the next execution can compare against it.

```bash
make run -- index
```

The second execution may report that the index is up to date if no compatible file has changed.

### Search cache

The expensive part of a search is not BM25 scoring, but preparing the index: tokenizing all chunks, counting frequencies, and calculating average length. This work depends only on the index, not on the question, so it is performed only once. `Search.prepare()` in `search.py` manages it as follows:

1. `prepare()` loads the JSON, tokenizes the query, and calls `_load_cache` before doing anything else.
2. The cache is one Pickle per index (`search_cache_py.pkl`, `search_cache_md.pkl`, or `search_cache_all.pkl`) inside `data/processed/cache/`.
3. Each Pickle stores the tokens for every chunk, term frequencies, document frequencies, average length, and a fingerprint of the index files (path, size, and modification time).
4. When loading, it compares the stored fingerprint with the current one. If they match, all data is reused and tokenization is skipped. If they do not match, or the Pickle cannot be read, everything is recalculated and the cache is saved again.
5. The prepared index state is cached, never the result of an individual query. Therefore, in a dataset, the index is prepared once and reused by all questions.

### HTTP API

The API exposes search and answers over HTTP by reusing the `Search` and `Answer` classes from the command line. In `api.py`, the `RagApi` class creates the FastAPI application and registers the endpoints:

* `POST /search` receives a Pydantic `SearchRequest` body with `{"query": "...", "k": 5}`, validates that the query is not empty and that `k` is positive (HTTP 400 otherwise), runs `Search.prepare()` using the cache, and returns a list of `MinimalSource` objects.
* `POST /answer` uses the same body to build the context with `Answer`. If no sources are retrieved, it returns HTTP 404; otherwise, it builds the prompt, generates the answer with Qwen, and returns an `AnsweredQuestion`.
* `/docs` provides FastAPI's automatic documentation.

Start the API with:

```bash
make run -- serve
```

## Known limitations

* Retrieval is lexical. A heavily paraphrased question with no shared terms may fail to retrieve the correct source.
* Qwen/Qwen3-0.6B is a small local model, so answers may be incomplete even when retrieval is correct.
* Overlap repeats a small amount of text between neighboring chunks, although every stored chunk respects the configured maximum size.
* The project currently uses Qwen/Qwen3-0.6B as its generation model.

Future improvements could include semantic embeddings with a lightweight model and a hybrid ranker combining lexical and semantic retrieval.

## Resources and AI usage

### Technical references

The implemented retrieval algorithm and RAG flow are based on techniques documented in:

* Lewis et al., _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks_ (2020): [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)
* Robertson and Zaragoza, _The Probabilistic Relevance Framework: BM25 and Beyond_ (2009): [https://doi.org/10.1561/15000019](https://doi.org/10.1561/15000019)
* Manning, Raghavan, and Schütze, _Introduction to Information Retrieval_: [https://nlp.stanford.edu/IR-book/](https://nlp.stanford.edu/IR-book/)

These original sources were not consulted directly during development. They are cited as references for the techniques implemented; the explanation of those techniques was developed with the AI assistance described below.

### Tools and dependencies

Links to the documentation for the tools used by the code:

* vLLM documentation: [https://docs.vllm.ai](https://docs.vllm.ai)
* Qwen/Qwen3-0.6B: [https://huggingface.co/Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B)
* Hugging Face Transformers pipelines: [https://huggingface.co/docs/transformers/main_classes/pipelines](https://huggingface.co/docs/transformers/main_classes/pipelines)
* Pydantic documentation: [https://docs.pydantic.dev](https://docs.pydantic.dev)
* Python Fire: [https://github.com/google/python-fire](https://github.com/google/python-fire)
* uv documentation: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
* FastAPI documentation: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)

The corpus is the public vLLM 0.10.1 repository. The public and private datasets and the moulinette are materials provided by 42.

### AI usage

AI was used as a learning and support tool, not as a substitute for understanding. It was used to:

* explain RAG, BM25, `transformers`, and the generation flow;
* identify and explain the quadratic calculation of average length;
* review input validation and edge cases;
* compare the implementation with the assignment requirements;
* help structure and document the project.

The design decisions, implementation, tests, and performance measurements were reviewed and understood before being included in the project.

<br>

## Fundación Telefónica

To run the program on Fundación Telefónica computers, create a script that directs caches and the environment to `goinfre`. Do not use `sgoinfre`.

You can check the current cache location with:

```bash
uv cache dir
```

### Local environment configuration

1. Create a file called `set-local.sh`.
2. Write and save the following content:

```bash
export CALLME_STORAGE="/home/aitorres/goinfre/RAG"

export UV_CACHE_DIR="$CALLME_STORAGE/uv-cache"
export UV_PROJECT_ENVIRONMENT="$CALLME_STORAGE/venv"
export UV_PYTHON_INSTALL_DIR="$CALLME_STORAGE/python"

export HF_HOME="$CALLME_STORAGE/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"

export TMPDIR="$CALLME_STORAGE/tmp"
export XDG_CACHE_HOME="$CALLME_STORAGE/xdg-cache"
```

3. Run the script with `source`:

```bash
source set-local.sh
```

4. Check the cache location again:

```bash
uv cache dir
```

The displayed path should point to `goinfre`. This allows `uv` and the other tools to install and store their dependencies outside the machine's limited storage space.

<br>

## Running the project with the moulinette

### Retrieval evaluation

1. Create your main `RAG` folder.
2. At its root, create a `student` folder and copy the repository into it. It must contain `data/datasets` and `data/raw/vllm-0.10.1`.
3. At the root, create the `data` folder and, inside it, `datasets`. Inside `datasets`, copy `private` and its contents from the `datasets_private.zip` file.
4. At the root, place `exams.zip` and `moulinette.zip`. Then extract `unzip exams.zip` and `unzip moulinette.zip`.
5. Run:

```bash
./exams/scripts/exam_retrieval.sh --student-path ./student --moulinette-path ./moulinette-ubuntu
```

6. A four-phase test will be generated. At the end, `STATUS: PASS` will be displayed if everything is correct.

### Answer Quality assessment

```bash
./exams/scripts/exam_answer.sh \
--student-path ./student \
--moulinette-path ./moulinette-ubuntu
```

1. Run the command from the root directory.
2. Wait until phase 2, `questions`.
3. Choose three questions marked as `VALID` and submit them one by one.
4. Generate the three answers using `answer`.
5. Finish with the evaluation summary.

### System Reliability

```bash
./exams/scripts/exam_edge_cases.sh --student-path ./student
```

This runs several edge-case tests. If everything is correct, the final result will be:

```text
====
 FINAL RESULT: 4/4
====
Results saved to: /home/aitorres/42madrid/****/evaluations/edge_cases/2026-09-29_01-35-40
STATUS: PASS
```
