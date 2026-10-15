# ONSJBJK Algorithm Finder

Experimental deterministic Python algorithm-structure recognition using Semgrep's OCaml generic AST, Python, SWI-Prolog and SQLite.

The repository contains three related components:

| Directory | Responsibility |
| --- | --- |
| `semgrep_prolog_poc/` | AP2–AP10: existing structural AST-to-Prolog extraction, exact reference matching, and compositional recognition. |
| `onsjbjk_algo_io_fallback_poc_v0_1/` | Independent input/output relationship experiment and SWI-Prolog candidate-family routing. |
| `algo_reference_corpus/` | AP11 immutable reference ingestion and AP12 separate automatic-fallback/full-corpus orchestration. |

## Why publish this?

To provide a small, inspectable example of *combining* AST structure, dependency observations and relational matching without machine-learning inference. It may be useful for program-analysis experiments, teaching, or further work on distinguishing interleaved computation threads.

## Prerequisites

- Windows CMD and Python (tested in the developer's Conda environment).
- Semgrep CLI, SWI-Prolog (`swipl`) and Git.
- A locally cloned TheAlgorithms/Python checkout **only for the ingestion features**. It is intentionally **not included** in this repository.

From `algo_reference_corpus/`, see `RUN_AP11_DOWNLOAD.cmd`, `RUN_AP12_SELFTEST.cmd`, `RUN_AP12_FULL.cmd`, `RUN_AP12_VERIFY.cmd`, and `RUN_AP12_SCAN.cmd`.
From `semgrep_prolog_poc/`, see `RUN_AP10_ACCEPTANCE.cmd`.
From `onsjbjk_algo_io_fallback_poc_v0_1/`, see `RUN_FALLBACK_POC.cmd`.

## Cautions

- Output labels are structural *candidates*, not proof of program correctness, mathematical invariants, or semantic equivalence.
- `UNKNOWN` and parser failures are not silently converted to successful algorithm recognition.
- Pilot evidence includes 11/11 live fallback tests and a five-source AP12 ingestion run; this does **not** demonstrate full-repository acceptance or generalization accuracy.
- Keep generated databases and `.pl` output artifacts outside version control. The reference checkout must stay independently reproducible.
- Review any files for credentials, personal details and intellectual-property obligations before making a public commit.
- No project-wide redistribution license is claimed by this template. The repository owner must choose a license after checking rights and attributions.

External project: [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python). This repository does not bundle that third-party checkout.
