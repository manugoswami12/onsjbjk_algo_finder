# Static logic-trace router with I/O fallback (v0.2)

## How to run (step by step)

This guide takes you from a fresh checkout to the final report. All commands are run from this folder,
`onsjbjk_algo_io_fallback_v0_2/`, unless a step says otherwise. Where Windows and Linux/macOS differ, both are shown.
The source code you analyse is **never executed**: only its Prolog translation runs.

### 1. Install the tools

| Tool | Needed for | Check that it works |
|---|---|---|
| Python 3.12 or newer | everything | `python --version` |
| SWI-Prolog 9 (`swipl` on your PATH) | everything | `swipl --version` |
| The Python package from `polyglot_logic/requirements.txt` | reading source code in every language | see below |
| ECL (Embeddable Common Lisp) | Common Lisp files (optional) | `ecl --version` |
| GHC (Glasgow Haskell Compiler) | Haskell files (optional) | `ghc --version` |
| git | downloading the two data sets | `git --version` |

Install the Python package and download the language grammars once. The commands are the same on every system. On
Windows you may write `..\` instead of `../`.

```
cd ../polyglot_logic
python -m pip install -r requirements.txt
python tools/cli.py prefetch
cd ../onsjbjk_algo_io_fallback_v0_2
```

If ECL or GHC is missing, Lisp or Haskell files simply count as "not analysable". Nothing breaks.

### 2. Get the data (kept outside this repository)

Two data sets are used. Neither is committed here.

**a) TheAlgorithms/Python**, the code the system learns from. It is pinned to one commit, so results are
reproducible:

```
git clone https://github.com/TheAlgorithms/Python C:\data\TheAlgorithms-Python
cd C:\data\TheAlgorithms-Python
git checkout e1a2a8b0
```

**b) Rosetta Code**, other people's code in many languages, used only for testing. This command fetches just the
tasks that are needed, into a folder you choose (here `C:\data\rosetta`):

```
python -c "import json, sys; sys.path.insert(0, '../polyglot_logic/tools'); import rosetta_eval; from pathlib import Path; rosetta_eval.fetch(Path(sys.argv[1]), list(json.load(open('../polyglot_logic/benchmark/rosetta_truth.json'))['tasks']))" C:\data\rosetta
```

Then tell the commands where the two folders are. Set these in every new terminal:

| Windows CMD | Linux/macOS |
|---|---|
| `set CORPUS=C:\data\TheAlgorithms-Python` | `export CORPUS=~/data/TheAlgorithms-Python` |
| `set ROSETTA=C:\data\rosetta` | `export ROSETTA=~/data/rosetta` |
| `set PYTHONPATH=.` | `export PYTHONPATH=.` |

Below, `%CORPUS%` is the Windows form; on Linux/macOS write `$CORPUS` instead, and likewise for `ROSETTA`.

### 3. Quick self-check (about 2 minutes)

```
python -m unittest tests.test_library_names tests.test_uniform
```

You should see `OK` at the end.

### 4. Try it on one file of your own

To ask "what does this program compute?" about any Python, C, Common Lisp or Haskell file:

```
python -c "import sys; sys.argv.append('--v03'); sys.path[:0] = ['.', 'tools_manual']; from pathlib import Path; from decide_new_or_known import decide; d = decide(Path(sys.argv[1])); print(d['decision'], d.get('class', ''), d.get('why', ''))" path\to\your_file.py
```

It prints one of three answers:

| Output | Meaning |
|---|---|
| `new_version sorting` (or `gcd`, `search`, `factorial`, ...) | Your program computes this known class, checked on many test inputs. |
| `new_algorithm` | It runs on every input, but no known class fits: a **new algorithm or an incorrect implementation**. These two cannot be told apart. |
| `undecided ...` and a reason | It could not be checked, e.g. `a root does not run on every input`. |

For example, the Rosetta Haskell gnome sort gives `new_version sorting`, and a binary gcd in Python gives
`new_version gcd`.

### 5. Run the main pipeline (learning and identification)

| Step | Command | What it does | Writes |
|---|---|---|---|
| 5a | `python eval_ta.py %CORPUS% --learn` | Learns every algorithm of TheAlgorithms/Python | `prolog/learned_ta.pl` |
| 5b | `python eval_ta.py %CORPUS% --run` | Names every TheAlgorithms file with what it learned | `benchmark/ta_answers.json` |
| 5c | `python eval_ta.py %CORPUS% --heldout %ROSETTA%` | Names every Rosetta test file (new code) | `benchmark/ta_heldout.json` |
| 5d | `python eval_ta.py %CORPUS% --status` | Checks every label | `benchmark/ta_status.json`, `benchmark/ta_result.md` |

The full corpus has 1346 files, so steps 5a–5c can take an hour or more on a laptop. `--workers N` sets how many
run in parallel (default 4).

### 6. Run the separate fallback (class decisions and learned branches)

This part never changes the pipeline's answers. It only adds answers where the pipeline said UNKNOWN.

```
python -c "import json; json.dump(sorted(json.load(open('benchmark/ta_heldout.json'))), open('held_files.json', 'w'))"
python -c "import json, sys, ta_corpus; from pathlib import Path; json.dump(sorted(ta_corpus.files(Path(sys.argv[1]))), open('corpus_files.json', 'w'))" %CORPUS%

python tools_manual/decide_new_or_known.py %ROSETTA% held_files.json held_decided.json --v03
python tools_manual/decide_new_or_known.py %CORPUS% corpus_files.json corpus_decided.json --v03

python tools_manual/write_branches.py corpus_decided.json
python eval_proposed.py held_decided.json corpus_decided.json
python eval_decision.py held_decided.json corpus_decided.json node
```

What these commands do:
- The first two lines make the lists of files to check.
- `decide_new_or_known.py` checks each file's class. It takes tens of minutes per set.
- `write_branches.py` turns each class found in TheAlgorithms into a Prolog branch in `prolog/proposed_branches.pl`.
- `eval_proposed.py` tests those branches.
- `eval_decision.py` gives every test file an answer.

### 7. Write the final report

```
python final_report.py %CORPUS% held_decided.json
```

Then open the reports, in this order:
1. `benchmark/FINAL_REPORT.md`: precision, recall, false positives and false negatives on learnt and new code, and
   why files were not analysable.
2. `benchmark/decision_fallback.md`: the answer for every test file.
3. `benchmark/proposed_fallback.md`: the learned branches and where they fired.

### 8. Reading the answers

| Answer | Meaning |
|---|---|
| an algorithm name (`bubble_sort`, `Binary-search`) | The pipeline recognised the specific algorithm. |
| a class (`sorting`, `gcd`) | The program computes this, checked on its outputs. Which sort it is, is not claimed. |
| new or incorrect implementation | It runs fully, but no known class fits. |
| variation of family F | Its logic structure belongs to family F (a tree node), but no rule there matched. |
| not analysable | Neither its structure nor its outputs could be checked (a GHCi transcript, a fragment, a missing package, ...). It is left out of the score. |
| UNKNOWN | The system will not guess. |

### 9. Troubleshooting

- **`swipl` not found:** add SWI-Prolog's `bin` folder to PATH, e.g. `set "PATH=C:\Program Files\swipl\bin;%PATH%"`.
- **Errors about tree-sitter or a language grammar:** rerun step 1, including `python tools/cli.py prefetch`.
- **Every Lisp or Haskell file is "not analysable":** ECL or GHC is not installed or not on PATH.
- **A run is slow:** this is normal for the full corpus. Run it in a second terminal, or start with
  `python eval_ta.py %CORPUS% --run --dir sorts` (one folder only).

This folder is a copy of `onsjbjk_algo_io_fallback_poc_v0_1/`, extended. The original folder is not modified. The v0.1 files are kept unchanged here (`run_poc.py`, `static_trace.py`, `prolog/route.pl`, `RUN_FALLBACK_POC.cmd`). The v0.2 files sit next to them:

| File | Role |
|---|---|
| `static_trace_v2.py` | v0.1 analysis plus the new witnesses |
| `prolog/route_v2.pl` | v0.1 rules plus the new broad → narrow branches |
| `run_v2.py` | runner, report with the I/O fallback, 36-case selftest |
| `RUN_FALLBACK_V02.cmd`, `RUN_STATIC_SELFTEST_V02.cmd` | Windows runners |
| `docs/01_V02_REQUIREMENTS_DESIGN.md` | requirements, branch tree, pseudocode, classification, critical and problems tables |

**Windows CMD:**

```cmd
conda activate ons_ruleskg
set "PATH=A:\swipl\bin;%PATH%"
cd /d <path>\onsjbjk_algo_io_fallback_v0_2
call RUN_FALLBACK_V02.cmd
call RUN_FALLBACK_V02.cmd examples\sieve.py
call RUN_STATIC_SELFTEST_V02.cmd
python -m unittest discover -s tests -v
```

**Branches.** The v0.1 branches are unchanged:
- `sequence_rearrangement`, `comparison_driven_reordering`;
- `indexed_lookup`, `interval_lookup`.

v0.2 adds these, written as broad family → narrow branches:

| Broad family | Narrow branches |
|---|---|
| `comparison_driven_reordering` (from v0.1) | `shift_insertion`, `selection_exchange` |
| `membership_lookup` | none |
| `aggregate` | `element_accumulation`, `extremum_search` |
| `recurrence` | `fibonacci_like`, `euclid_like`, `factorial_like`, `series_sum` |
| `recursive_decomposition` | none |
| `number_property` | `digit_processing`, `divisor_search`, `collatz_like` |
| `marking` | `sieve_like` |
| `symmetric_compare` | `palindrome_check` |

When no family has evidence, the router answers `unknown` and the report prints `IO FALLBACK`, the input→output dependence of the returns.

These are candidate branches, not proofs of algorithm identity. Unknown source is never executed. No packages beyond Python 3 and SWI-Prolog are needed.

## Learning and final results

- `learn_v2.py`: new learner (AST normalisation + winnowing, nearest neighbour).
- `compare_learners.py`: v0.2 also uses the original AP13 learners from `polyglot_logic` (read-only):
  `learn-dir` (exact traced logic) and `io_catalog` (behaviour; runs a Prolog translation on fixed inputs).
- `eval_heldout.py <checkout> <truth.json> [--kb kb/learned.json] [--learner iocat --train T1.json ...]`

| Test (TheAlgorithms/Python, keys frozen first) | Precision | Recall |
|---|---|---|
| 15 files (used for fixes, not held-out) | 100% | 100% |
| 55 files, witnesses only | 81.8% | 47.4% |
| fresh 55, witnesses + io_catalog | 87.5% | 56.0% |
| **final 101, witnesses + io_catalog** | **66.7%** | **33.3%** |

See `benchmark/learner_comparison.md` and `benchmark/final101_result.md`.

## All of TheAlgorithms/Python (doc 04 section 17)

Every algorithm of TheAlgorithms/Python (commit e1a2a8b0) is learned from Python and then tested. A label that
learning gets wrong gets a hand-written rule, the same in every language:
- general relations in `prolog/ta_rules.pl`;
- file rules in `prolog/ta_file_rules.pl`.

The scripts:
- `ta_corpus.py`, `eval_ta.py` and `learn_apply.py` do the learning and testing;
- `ta_distinct.py` writes the file rules;
- `ta_prompts.py` writes one prompt per rule (`docs/RULE_PROMPTS.md`) for writing the same kind of rule in future.

Result: 1344 of the 1344 analysable files are identified (0 false positives, 0 false negatives). Two files with no
algorithm code are not scored, and files with identical logic count as one.

## Separate fallback for new code (doc 04 section 18; never loaded by the pipeline)

| File | Role |
|---|---|
| `prolog/class_specs.pl`, `ta_classes.py` | Class relations (sorting, search, gcd, lcm, factorial, Fibonacci, prime check, ...), checked on the program's runs on fixed inputs (`sum(2,3,X)` style). |
| `prolog/call_roots.pl`, `tools_manual/decide_new_or_known.py` | Decide on the file's root functions only. "New version of a known class" needs every root to run on every input, one relation to hold and a tree node. Otherwise the answer is "new or incorrect implementation", or undecided. |
| `tools_manual/write_branches.py`, `prolog/proposed_branches.pl`, `eval_proposed.py` | Each class decision on a TheAlgorithms file becomes a Prolog branch at its tree node: `proposed_branch(Node, Class) :- class_holds(Class).` |
| `prolog/library_names.pl`, `ta_library.py`, `eval_library.py` | A program whose whole computation is one library call is named by that library's algorithm. |
| `pnf_v03.py`, `prolog/interp_v03.pl`, `prolog/run_main_v03.pl` | v0.3 runner: AP13's lowerer and interpreter extended, not edited. It adds lambdas and closures, module-level constants, generator arguments, and `str`/`set`/`chain`/`zip`/`bisect`. |
| `eval_decision.py`, `final_report.py` | Give every held-out file an answer, and write `benchmark/FINAL_REPORT.md` under the reporting criteria. |

Results: 39 of 39 held-out class decisions are right, 14 of 14 branch firings are right, and all 37 class claims on
TheAlgorithms are right.

| New code (held-out Rosetta) | analysable files | precision | recall (analysable) | recall (all files) |
|---|---|---|---|---|
| C | 34 of 69 | 96.9% | 91.2% | 44.9% |
| Common Lisp | 46 of 75 | 97.8% | 95.7% | 58.7% |
| Haskell | 42 of 144 | 94.3% | 78.6% | 22.9% |
| Python | 83 of 162 | 91.5% | 78.3% | 40.1% |
| **all** | **205 of 450** | **94.5%** | **84.4%** | **38.4%** |

All 10 wrong answers on new code come from the main pipeline. The separate fallback made none.

To reproduce every number above, follow [How to run (step by step)](#how-to-run-step-by-step) at the top of this file.

Limits:
- **A class, not which algorithm.** A class relation says "sorting", not which sort.
- **A new algorithm cannot be told from an incorrect implementation.** Both are reported as "new or incorrect
  implementation".
- **Code that does not run on every input is not analysed.** This covers GHCi transcripts, fragments, missing
  packages, type errors, curried Python, and strings as character codes.
- **One implementation per algorithm to learn from.** New styles often land on broad tree nodes.
