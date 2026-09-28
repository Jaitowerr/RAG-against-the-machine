# Exam Scripts Instructions: Corrector Guide

This document explains how to use the exam scripts during correction of
Project 2: RAG Against the Machine. All exam scripts are located in `exams/scripts/`.

---

## Prerequisites

Before running any exam script:

1. **Install student dependencies**:
   ```bash
   cd student && uv sync
   ```

2. **Unzip private datasets** (if not already done):
   ```bash
   unzip data/datasets/datasets_private.zip -d data/datasets/
   ```

3. **Verify student code** does not import moulinette packages (match imports
   only, so the word in a comment or docstring is not a false positive):
   ```bash
   grep -rnE "^[[:space:]]*(import|from)[[:space:]]+moulinette" student/ --include="*.py"
   ```

4. **Set up moulinette** (pick one):
   - **Using the binary**: `moulinette-ubuntu` or `moulinette-fedora` from the moulinette zip
   - **Using the source**: `cd moulinette && uv sync`

---

## Recommended Correction Flow (~35 min)

The scale is designed so the automated retrieval pipeline runs in the background
while you inspect code. Follow this flow:

1. **Q1**: Preliminaries & Setup (git repo, uv sync, unzip private datasets)
2. **Q2**: Launch Pipeline: start `exam_retrieval.sh` in a **background terminal** (~8 min)
3. **Q3**: Code Quality & Pydantic Models review (while the pipeline runs)
4. **Q4**: Chunking Strategies (ask the student to show the 2 strategies)
5. **Q5**: Retrieval System (live demo with a search query)
6. **Q6**: Answer Generation (run a test answer)
7. **Q7**: Docs Recall@5 from `exam_retrieval.sh` (pass: >= 80%)
8. **Q8**: Code Recall@5 from `exam_retrieval.sh` (pass: >= 50%)
9. **Q9**: Answer Quality: run `exam_answer.sh`, judge 3 answers (pass: 2/3)
10. **Q10**: Student Understanding (ask the 5 questions)
11. **Q11**: README & Documentation review
12. **Q12**: System Reliability: run `exam_edge_cases.sh` (~1 min)
13. **Q13**: Bonus (graded only if the whole mandatory part is validated)

---

## Exam Scripts Overview

| Script | Tests | Pass Criteria | Duration |
|--------|-------|---------------|----------|
| `exam_retrieval.sh` | Indexing, throughput, Recall@5 | All 4 tests pass | ~8 min |
| `exam_answer.sh` | Answer quality (semi-automated) | 2/3 answers satisfactory | ~5 min |
| `exam_edge_cases.sh` | Edge case handling | All 4 tests pass | ~1 min |

All scripts are run from the project root directory.
All scripts accept `--module-name NAME` to override the Python module name
(default: `src`). Use this if the student named their module differently.

---

## 1. Retrieval Exam (`exams/scripts/exam_retrieval.sh`)

### What it tests

| Test # | Name | Criterion |
|--------|------|-----------|
| 1 | Indexing | Completes in <= 300s (5 min) |
| 2 | Warm retrieval throughput | 200 questions in <= 90s |
| 3 | Docs Recall@5 | >= 80% |
| 4 | Code Recall@5 | >= 50% |

### How to run

```bash
# Using moulinette source directory
./exams/scripts/exam_retrieval.sh \
    --student-path ./student \
    --moulinette-path ./moulinette

# Using moulinette binary
./exams/scripts/exam_retrieval.sh \
    --student-path ./student \
    --moulinette-path ./moulinette-ubuntu
```

### Output

The script prints the exact Recall@5 values and a PASS/FAIL per test. Use the
Docs value for Q7 (pass at >= 80%) and the Code value for Q8 (pass at >= 50%).

Recall is computed by the moulinette using the Intersection over Union (IoU) of
character ranges within the same file, with a match threshold of IoU > 0.05.

### Results directory

```
evaluations/retrieval/<YYYY-MM-DD_HH-MM-SS>/
  indexing_stdout.log       # Indexing output
  indexing_stderr.log       # Indexing errors
  search_docs_stdout.log    # Docs search output
  search_code_stdout.log    # Code search output
  search_results/           # Student search result files
  docs_eval.log             # Moulinette evaluation (docs)
  code_eval.log             # Moulinette evaluation (code)
  summary.log               # Per-test PASS/FAIL
```

---

## 2. Answer Exam (`exams/scripts/exam_answer.sh`)

### What it tests

Uses `list_valid_questions` to show which questions have their sources correctly
retrieved, then lets you pick 3 questions to test answer generation.

### How to run

```bash
# Interactive mode (pick questions during run)
./exams/scripts/exam_answer.sh \
    --student-path ./student \
    --moulinette-path ./moulinette

# Pre-selected questions
./exams/scripts/exam_answer.sh \
    --student-path ./student \
    --moulinette-path ./moulinette \
    --questions "What is PagedAttention?,How to deploy vLLM?,What models does vLLM support?"
```

### Pass criteria

2 out of 3 answers must be satisfactory (this maps to scale Q9). The mandatory
Qwen/Qwen3-0.6B model has known reasoning limits, so grading prioritizes retrieval
quality and grounding over perfect phrasing.
A satisfactory answer should:
- be coherent and understandable,
- be mostly grounded in the retrieved sources (no major hallucination),
- address the question asked.

Minor incompleteness due to base-model limitations is acceptable.

---

## 3. Edge Cases Exam (`exams/scripts/exam_edge_cases.sh`)

### What it tests

| Test # | Name | Input |
|--------|------|-------|
| 1 | Empty query | `search "" --k 10` |
| 2 | Gibberish query | `search "asdfghjkl" --k 10` |
| 3 | k=0 | `answer "What is vLLM?" --k 0` |
| 4 | Bad dataset path | `search_dataset --dataset_path /nonexistent.json` |

### How to run

```bash
./exams/scripts/exam_edge_cases.sh --student-path ./student
```

### Pass criteria

All 4 tests must complete without Python tracebacks. The program may print
error messages or return empty results, and that is acceptable. What is NOT
acceptable is an unhandled exception with a traceback.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `uv sync` fails | Check Python version matches `.python-version` |
| Private datasets missing | Run `unzip data/datasets/datasets_private.zip -d data/datasets/` |
| Moulinette binary not executable | Run `chmod +x moulinette-ubuntu` |
| Search results not found | Check `data/output/search_results/` for output files |
| Indexing too slow | May indicate missing index caching; check with student |
| Edge case test hangs | The student may have an infinite loop; Ctrl+C and mark as FAIL |
