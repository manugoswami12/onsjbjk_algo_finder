# ONSJBJK Algorithm Finder

Experimental deterministic Python algorithm-structure recognition using Semgrep's OCaml generic AST, Python, SWI-Prolog and SQLite.

The repository contains five related components:

| Directory | Responsibility |
| --- | --- |
| `semgrep_prolog_poc/` | AP2–AP10: existing structural AST-to-Prolog extraction, exact reference matching, and compositional recognition. |
| `onsjbjk_algo_io_fallback_poc_v0_1/` | Independent input/output relationship experiment and SWI-Prolog candidate-family routing. |
| `algo_reference_corpus/` | AP11 immutable reference ingestion and AP12 separate automatic-fallback/full-corpus orchestration. |
| `polyglot_logic/` | AP13 multi-language logic tracing: learn from Python, recognise the same traced logic in Rust, Java, C, R, Haskell, Common Lisp and Prolog (tree-sitter + SWI-Prolog; reuses the AP12 router unchanged). |
| `onsjbjk_algo_io_fallback_v0_2/` | Learns every algorithm of TheAlgorithms/Python (by extending AP13, which it does not edit). It is tested on held-out Rosetta Code in Python, C, Common Lisp and Haskell. A separate fallback decides an algorithm's class from its input→output relation and writes it as a Prolog branch. |

## Results (v0.2, `onsjbjk_algo_io_fallback_v0_2/benchmark/FINAL_REPORT.md`)

| | files scored | correct | false positives | false negatives | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| Learnt code: TheAlgorithms/Python | 1344 of 1346 | 1344 | 0 | 0 | 100% | 100% |
| New code: held-out Rosetta (4 languages) | 205 of 450 | 173 | 10 | 32 | 94.5% | 84.4% (38.4% on all 450) |

Reporting criteria:
- **Code the system cannot analyse is not scored.** A held-out file is not analysable when the pipeline gave no answer
  and none of its functions runs on every test input. A TheAlgorithms file is not analysable when it has no algorithm
  code at all.
- **Files with identical logic count once.** Naming either of their labels is right.
- **Wrong answers are never excluded.**
- The all-files figure is always given beside the analysable one. Per-language numbers are in the report.

## Why this matters

A single person built it, with only Python and SWI-Prolog. Every program is turned into the same language-neutral
Prolog normal form, including Common Lisp (through ECL) and Haskell (through GHC Core). The same algorithm then
becomes the same Prolog term, whatever language it was written in. Algorithms are known by their logic structure (a
tree of families and branches). Their behaviour is known by class relations, used in either direction like
`sum(2, 3, X)`: compute the output from the input, or check a given output.

This is meant to grow into a uniform, checkable **knowledge base of algorithm logic**. People and AI coding agents
would use it to *design* code from known, verified parts, for example composing A* search with gcd, instead of
starting every program from nothing. Recognition and the class relations exist today. Composing components into new
designs is the intended next use and is not built yet.

## Why publish this?

To provide a small, inspectable example of *combining* AST structure, dependency observations and relational matching without machine-learning inference. It may be useful for program-analysis experiments, teaching, or further work on distinguishing interleaved computation threads.

## Prerequisites

- Windows CMD and Python (tested in the developer's Conda environment).
- Semgrep CLI, SWI-Prolog (`swipl`) and Git.
- A locally cloned TheAlgorithms/Python checkout **only for the ingestion features**. It is intentionally **not included** in this repository.

From `algo_reference_corpus/`, see `RUN_AP11_DOWNLOAD.cmd`, `RUN_AP12_SELFTEST.cmd`, `RUN_AP12_FULL.cmd`, `RUN_AP12_VERIFY.cmd`, and `RUN_AP12_SCAN.cmd`.
From `semgrep_prolog_poc/`, see `RUN_AP10_ACCEPTANCE.cmd`.
From `onsjbjk_algo_io_fallback_poc_v0_1/`, see `RUN_FALLBACK_POC.cmd`.
For `onsjbjk_algo_io_fallback_v0_2/`, follow **"How to run (step by step)"** at the top of
[its README](onsjbjk_algo_io_fallback_v0_2/README.md). It covers installing the tools, getting the two data sets,
checking a file of your own, the full run, and reading the final report.

## Cautions

- Output labels are structural *candidates*, not proof of program correctness, mathematical invariants, or semantic equivalence.
- `UNKNOWN` and parser failures are not silently converted to successful algorithm recognition.
- The v0.2 class fallback is kept separate from the recognition pipeline and never changes its answers. It names a
  class ("sorting"), not a specific algorithm. A program that runs but satisfies no known relation is reported as "new
  or incorrect implementation": the two cannot be told apart.
- Pilot evidence includes 11/11 live fallback tests and a five-source AP12 ingestion run; this does **not** demonstrate full-repository acceptance or generalization accuracy.
- Keep generated databases and `.pl` output artifacts outside version control. The reference checkout must stay independently reproducible.
- Review any files for credentials, personal details and intellectual-property obligations before making a public commit.
- No project-wide redistribution license is claimed by this template. The repository owner must choose a license after checking rights and attributions.

External project: [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python). This repository does not bundle that third-party checkout.
