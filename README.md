# ONSJBJK Algorithm Finder

**What it does:** you give it a program (Python, C, Common Lisp or Haskell), and it tells you which algorithm the
program is, or at least what it computes ("this is a sort", "this is a gcd").
- It does not use machine learning.
- It does not run your program. It turns the program into Prolog, and SWI-Prolog checks that.
- When it is not sure, it says UNKNOWN instead of guessing.

It learned every algorithm in [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python). It was then tested on
other people's code from [Rosetta Code](https://rosettacode.org) in four languages:

| | correct | wrong | precision | recall |
|---|---|---|---|---|
| Code it learned from (1344 TheAlgorithms files) | 1344 | 0 | 100% | 100% |
| New code it never saw (206 analysable Rosetta files) | 177 | 3 | 98.3% | 85.9% (39.3% of all 450 files) |

Recall counts the 206 files the system can evaluate. Of the other 244 held-out files, 66 are fragments (a few lines,
or no function); the other 178 define real algorithms the evaluator cannot run yet (an in-place void function on an
array plus a length, GMP, Python 2, Haskell operator definitions): later-stage work. Over every file that is not a
fragment, recall is 177 of 384 = 46.1%; precision is the same 98.3%.

Honest note on the new-code row: 12 hand-built branches of the tree (Ackermann, knapsack, Caesar, matrix product,
run-length, N-queens, Josephus, leap year, LCS, Levenshtein, Roman numerals, Hanoi) were written from Rosetta
files of these same tasks, because the Python examples cannot teach those forms. Without them, relearned from
TheAlgorithms only, the pipeline names 114 of the 450 test files correctly and 10 wrongly (with them, before the
conversion fixes of doc 04 section 19: 158 and 10; with them: 163 and 3).

The full report is in [benchmark/FINAL_REPORT.md](benchmark/FINAL_REPORT.md). "Analysable" is explained in
[Reading the answers](#reading-the-answers).

---

## Contents of this repository

| Folder or file | What it is |
|---|---|
| `*.py`, `prolog/`, `tools_manual/` | The program. |
| `polyglot_logic/` | The part that reads source code in many languages and turns it into Prolog. The main program uses it. |
| `data/` | The two code collections used, **already included**, so you do not need to download anything. See `data/README.md`. |
| `vendor/tree-sitter/` | tree-sitter (the code reader) kept exactly as tested: the pip packages, the prebuilt grammars, all source code and checksums. Install it with `python vendor/tree-sitter/install_offline.py`. |
| `benchmark/` | The results. Start with `FINAL_REPORT.md`. |
| `tests/` | Automatic tests. |
| `docs/` | Design documents. Technical details are in `docs/04_LEARNING_DESIGN.md` and `docs/README_v02_details.md`. |
| `older_code/` | Earlier versions of the project, kept for history. Two small pieces of it are still loaded by `polyglot_logic/`, so do not delete it. |

---

## 1. Install what it needs (once)

You need **Python** and **SWI-Prolog**. **ECL** and **GHC** are optional: they are only needed to read Common Lisp
and Haskell files.

Tested with Python 3.13, SWI-Prolog 9.0.4, ECL 21.2.1 and GHC 9.4.7. tree-sitter 0.26.0 is installed from this
repository.

### Windows

1. **Python.** Download Python 3.12 or newer from https://www.python.org/downloads/ and run the installer. On its first
   screen, tick **"Add python.exe to PATH"**.
2. **SWI-Prolog.** Download the Windows 64-bit installer from https://www.swi-prolog.org/download/stable and run it.
   During setup, choose **"Add swipl to the system PATH"**.

   If you missed that option, add it to PATH yourself:
   - Press the Windows key, type *environment variables*, and open **"Edit the system environment variables"**.
   - Click **Environment Variables…**, select **Path** under *User variables*, then **Edit → New**.
   - Type `C:\Program Files\swipl\bin` (the folder that contains `swipl.exe`), then click OK three times.
   - Close and reopen the Command Prompt.

   To add it for the current window only:
   ```
   set "PATH=C:\Program Files\swipl\bin;%PATH%"
   ```
3. **Optional, for Haskell files.** Install GHC with GHCup from https://www.haskell.org/ghcup/. Common Lisp needs ECL,
   which is easiest to get on Linux or macOS.

### Linux (Debian or Ubuntu)

```
sudo apt update
sudo apt install python3 python3-pip swi-prolog-nox
sudo apt install ecl ghc          # optional: Common Lisp and Haskell
```

### macOS (with Homebrew from https://brew.sh)

```
brew install python swi-prolog
brew install ecl ghc              # optional: Common Lisp and Haskell
```

### Check the installation

Open a terminal (on Windows, the Command Prompt) and type:

```
python --version
swipl --version
```

Each command should print a version number. On Linux or macOS, type `python3` wherever this guide says `python`.

### Get the project and its Python package

```
git clone https://github.com/manugoswami12/onsjbjk_algo_finder.git
cd onsjbjk_algo_finder
python vendor/tree-sitter/install_offline.py
```

The last command installs **tree-sitter**, the code reader, exactly as it was tested. It needs no internet, because
everything is in `vendor/tree-sitter/`:
- the exact pip packages;
- the 8 language grammars, prebuilt for Windows, macOS and Linux;
- all of their source code;
- a sha256 checksum for every file.

It ends with `done: tree-sitter is installed exactly as tested`.

If your computer is not Windows x86-64, macOS or Linux x86-64, use the online install instead. It gets the same pinned
versions:
```
python -m pip install -r polyglot_logic/requirements.txt
python polyglot_logic/tools/cli.py prefetch
```

From here on, **every command is typed in the `onsjbjk_algo_finder` folder.**

---

## 2. Check that it works (about 2 minutes)

```
python -m unittest tests.test_library_names tests.test_uniform
```

It ends with `OK`.

---

## 3. Try it on a program of your own

First set one helper variable. Do this once per terminal window:

| Windows | Linux / macOS |
|---|---|
| `set PYTHONPATH=.` | `export PYTHONPATH=.` |

Then run this, putting your file's path at the end:

```
python -c "import sys; sys.argv.append('--v03'); sys.path[:0] = ['.', 'tools_manual']; from pathlib import Path; from decide_new_or_known import decide; d = decide(Path(sys.argv[1])); print(d['decision'], d.get('class', ''), d.get('why', ''))" data/rosetta/Task/Sorting-algorithms-Gnome-sort/Haskell/sorting-algorithms-gnome-sort.hs
```

| It prints | It means |
|---|---|
| `new_version sorting` (or `gcd`, `search`, `factorial`, `prime_check`, …) | Your program computes this. It was checked on many test inputs. |
| `new_algorithm` | Your program runs, but it matches nothing known. It is either a **new algorithm or an incorrect implementation**, and the two cannot be told apart. |
| `undecided` and a reason | It could not be checked. For example, `a root does not run on every input`. |

The example file above prints `new_version sorting`. A binary gcd written in Python, such as
`data/rosetta/Task/Greatest-common-divisor/Python/greatest-common-divisor-5.py`, prints `new_version gcd`.

---

## 4. Reproduce all the results

Everything uses the included `data/` folder. Run the steps in order. Do step 3's `set PYTHONPATH=.` (Windows) or
`export PYTHONPATH=.` (Linux/macOS) first.

**a) Learn TheAlgorithms and name every file.** This is the main pipeline, and steps a1–a3 together can take an hour
or more:

| Step | Command | Writes |
|---|---|---|
| a1 | `python eval_ta.py data/TheAlgorithms-Python --learn` | `prolog/learned_ta.pl` (what was learned) |
| a2 | `python eval_ta.py data/TheAlgorithms-Python --run` | `benchmark/ta_answers.json` |
| a3 | `python eval_ta.py data/TheAlgorithms-Python --heldout data/rosetta` | `benchmark/ta_heldout.json` (the test files) |
| a4 | `python eval_ta.py data/TheAlgorithms-Python --status` | `benchmark/ta_status.json`, `benchmark/ta_result.md` |

**b) Decide the class of every file.** This is the separate fallback; it never changes the pipeline's answers. It
takes about 15 minutes for the test files and longer for TheAlgorithms:

```
python -c "import json; json.dump(sorted(json.load(open('benchmark/ta_heldout.json'))), open('held_files.json', 'w'))"
python -c "import json, ta_corpus; from pathlib import Path; json.dump(sorted(ta_corpus.files(Path('data/TheAlgorithms-Python'))), open('corpus_files.json', 'w'))"
python tools_manual/decide_new_or_known.py data/rosetta held_files.json benchmark/held_decided.json --v03
python tools_manual/decide_new_or_known.py data/TheAlgorithms-Python corpus_files.json benchmark/corpus_decided.json --v03
```

**c) Turn the classes into Prolog branches, and give every test file an answer:**

```
python tools_manual/write_branches.py benchmark/corpus_decided.json
python eval_proposed.py benchmark/held_decided.json benchmark/corpus_decided.json
python eval_decision.py benchmark/held_decided.json benchmark/corpus_decided.json node
```

**d) Write the final report (a few seconds):**

```
python final_report.py data/TheAlgorithms-Python benchmark/held_decided.json
```

The results of steps a–c are already included in `benchmark/`. So if you only want the report, step d alone is
enough.

---

## 5. Read the results

Open these in order:
1. **`benchmark/FINAL_REPORT.md`**: precision, recall, false positives and false negatives per language, and why some
   files were not analysable.
2. `benchmark/decision_fallback.md`: the answer for every test file.
3. `benchmark/proposed_fallback.md`: the Prolog branches that were learned, and where they fired.

### Reading the answers

| Answer | Meaning |
|---|---|
| an algorithm name (`bubble_sort`, `Binary-search`) | The specific algorithm was recognised. |
| a class (`sorting`, `gcd`) | The program computes this, checked on its outputs. Which sort it is, is not claimed. |
| new or incorrect implementation | It runs, but no known class fits. |
| variation of family F | Its logic structure is in family F, but no rule there matched. |
| not analysable | It could not be checked at all: a GHCi transcript, a code fragment, a missing library, a type error, or code the interpreter cannot run yet. It is not scored. |
| UNKNOWN | It will not guess. |

How the results are counted:
- Wrong answers are **never** removed from the score.
- Files with identical logic (two copies of the same code under different names) count as one.

### Limits

- A class names *what* is computed ("sorting"), not *which* algorithm.
- A new algorithm cannot be told apart from an incorrect implementation.
- Code that cannot run on the test inputs is not analysed.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `swipl` is not recognised | SWI-Prolog is not on PATH. See step 1 (Windows: add `C:\Program Files\swipl\bin`). |
| `ModuleNotFoundError` | Run commands from the `onsjbjk_algo_finder` folder, after `set PYTHONPATH=.` or `export PYTHONPATH=.`. |
| Errors about tree-sitter or a grammar | Run `python vendor/tree-sitter/install_offline.py` again. |
| Every Lisp or Haskell file is "not analysable" | ECL or GHC is not installed, or not on PATH. |
| A step is slow | That is normal for the full collections. You can try one folder first with `python eval_ta.py data/TheAlgorithms-Python --run --dir sorts`. |

---

## Why this matters

Every program is turned into the same language-neutral Prolog form, including Common Lisp (through ECL) and Haskell
(through GHC Core). The same algorithm then becomes the same Prolog term, whatever language it was written in.
Algorithms are known by their logic structure. Their behaviour is known by relations that can be used in either
direction, like `sum(2, 3, X)`.

The aim is a uniform, checkable **knowledge base of algorithm logic**. People and AI coding agents would use it to
*design* code from known, verified parts, for example A* search combined with gcd, instead of starting from nothing.
Recognition works today; composing parts into new designs is the next step.

## Licences

- The code in `data/` keeps its own licences: TheAlgorithms is MIT, and Rosetta Code is GFDL 1.2 (see
  `data/README.md`).
- No licence is yet chosen for the project's own code. The owner chooses one.
