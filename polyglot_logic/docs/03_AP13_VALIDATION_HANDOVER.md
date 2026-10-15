# AP13 Validation Handover (15 October 2026)

Every number below was measured in the development container. That container ran
Linux, Python 3.13, SWI-Prolog 9.0.4 and tree-sitter-language-pack 1.22.1.
The Windows office-PC run (`RUN_AP13_SELFTEST.cmd`) is still pending.

## 1. Acceptance criteria (doc 01 §9)
| Id | Result | Evidence |
|---|---|---|
| A1 | **PASS 11/11** | Each of the AP12 POC examples gives exactly the POC's expected route set. The facts come from tree-sitter, not Python `ast`. |
| A2 | **PASS 8/8** | Bubble sort is learned once from `examples/bubble/bubble.py`. Leaf `MATCH` in Python, Rust, Java, C, R, Haskell, Common Lisp and Prolog. |
| A3 | **PASS 8/8** | Binary search is learned once from `examples/binary_search/binary_search.py`. Leaf `MATCH` in all 8 languages. |
| A4 | **PASS 5/5** | Negatives give no leaf match, and no reordering or interval route: dead swap, wrong exchange (j/j+2), linear search, sum list, unrelated compare. |
| A5 | **PASS** | POC `mixed.py` matches both references. `semgrep_prolog_poc/examples/candidate.py` now leaf-matches binary search; AP11's strict scan reported UNKNOWN for it. |
| A6 | **PASS** | `learn-corpus` reads an AP11-format catalog without writing to it (byte-identical before and after). Two `sort` methods in two classes become distinct labels `…__A_sort` and `…__B_sort`. A rerun reports `already_present`. |
| A7 | **PASS** | When swipl is missing, `scan` exits with code 2 and the message `swipl not found`. It is never reported as UNKNOWN. |
| A8 | **PASS** | `git status` shows only the new `polyglot_logic/` folder and the one-row README addition. No AP2–AP12 file changed (§4). |

`RUN_AP13_SELFTEST`: 19 tests, all OK (offline, lowering and live tiers).

What the bindings show: names never matter. For example, Haskell bubble sort
matches with `xs, $cursor`, Prolog with `$arg0, $cursor` and Java with `a, j`. All
three bind to the reference's `items, j`.

## 2. Held-out evaluation: Rosetta Code (other people's code)
`RUN_AP13_ROSETTA` sparse-clones RosettaCodeData. That text is GFDL, so it is
**not committed**. The script then scans every solution of *Sorting algorithms /
Bubble sort* and *Binary search* in the 8 languages: 36 files.
References come only from the two Python examples above. The set was never edited.

| Run | Leaf MATCH | Expected branch routed | Wrong family | False MATCH | Errors |
|---|---|---|---|---|---|
| First measurement | 2/36 | 6/36 | 0 | 0 | 2 (Prolog lowerer crashed) |
| Final | **8/36** | **9/36**, plus 4 more routed to `indexed_lookup` | **0** | **0** | **0** |

Every improvement between the two runs is a general, semantics-preserving step.
None is per-file tuning:

- **Early-return control dependence (PDG).** After `if c: return`, the later
  statements run under `not c`.
- **Induction-variable index shift.** `swap(i-1, i)` is treated the same as
  `swap(j, j+1)`.
- **Strict-total-order consequences.** `a>b ⇒ a≠b`, and
  `¬(a>b) ∧ ¬(b>a) ⇒ a=b`.
- **New idioms.**
  - Java `do…while` and R `repeat` loops.
  - `x.compareTo(y) > 0` is read as `x > y`.
  - `(lo+hi) >>> 1` is read as `(lo+hi)/2`.
  - R vector swap `x[c(i,j)] <- x[c(j,i)]`.
  - `Some`/`Just`/`Ok` wrappers are transparent.
- **Robustness.**
  - Prolog 0-arity predicates are handled.
  - Nested control constructs and computed Lisp heads become explicit
    `unsupported` facts, not crashes.

Matched: Python, Rust, Java and C bubble sort; one Prolog bubble sort; Python,
Java and C binary search.

Not matched yet. Each reason is visible in the facts or the limitations:

| Not matched | Reason |
|---|---|
| Higher-order or library style: Python `findIndexBinary`, Haskell `foldr`/`until`, Lisp `loop` keywords other than `while`/`do`, Java generic `Comparable` variants | Not modelled by the lowering tables (P18) |
| Rust half-open interval `upper = mid` | A different variant from the learned reference. It routes only to `indexed_lookup`, which is correct. |
| R bubble sort | `repeat` loop with `break`, and a comparison hidden in an assignment inside `if` |

Conclusion: **precision held at 100%** on this set (0 false matches, 0 wrong
families). Recall is 8/36 at the leaf level. More reference variants and more
idiom tables will raise recall; the matching rules do not need to be loosened.

## 3. Opt-in execution check (`check`, R11)
| Command | Result |
|---|---|
| `check sort bubble.py bubble_sort bubble.c bubble_sort` | `IO_AGREEMENT 15/15` |
| `check search binary_search.py … binary_search.c binary_search` | `IO_AGREEMENT 30/30` |
| `check sort bubble.py … negative/wrong_exchange.c wrong_exchange` | `IO_AGREEMENT 5/15` (the negative is caught) |

The check runs Python and C candidates. Runners for the other 6 languages are
future work. It runs only when asked, in a temp directory with a timeout. It is
not a security sandbox.

## 4. Frozen code and existing suites (unchanged)
The baselines were measured *before* AP13 and again after. The results are identical:

| Suite | Before | After |
|---|---|---|
| `onsjbjk_algo_io_fallback_poc_v0_1/run_poc.py --selftest` | 11/11 PASS | 11/11 PASS |
| `algo_reference_corpus` unittest | 26 tests: 2 errors, 8 skipped | same |
| `semgrep_prolog_poc` unittest | 119 tests: 38 failures, 18 skipped | same |

The existing errors and failures belong to this container, not to AP13:
- Semgrep is not installed.
- The `TheAlgorithms_Python` checkout and the `out/ap10` artifacts are absent.
- SWI-Prolog 9.0.4 honours only one `-s` flag, which breaks the AP10 runners here.

AP13 avoids the last problem by loading all files through one `load_files/2` goal.
Your Windows SWI-Prolog previously passed those suites.

## 5. How to run (Windows CMD, `ons_ruleskg`)
```cmd
set "PATH=A:\swipl\bin;%PATH%"
cd /d "...\onsjbjk_office_wren_NT_ace_utool_clingo\polyglot_logic"
python -m pip install -r requirements.txt
call RUN_AP13.cmd prefetch
call RUN_AP13_SELFTEST.cmd
call RUN_AP13.cmd learn ref_bubble_py examples\bubble\bubble.py bubble_sort
call RUN_AP13.cmd learn ref_binary_py examples\binary_search\binary_search.py binary_search
call RUN_AP13.cmd scan examples\bubble\bubble.hs
call RUN_AP13.cmd scan "D:\any\new_code.rs"
call RUN_AP13.cmd learn-corpus ..\algo_reference_corpus\TheAlgorithms_Python ..\algo_reference_corpus\store --categories sorts searches
call RUN_AP13.cmd status
call RUN_AP13_ROSETTA.cmd
```
- **`prefetch`:** run it once while online. tree-sitter grammars download at first use (P13).
- **`learn-corpus`:** reads AP11 read-only. Expect many `no_effects` rows: functions that write no sequence, perform no exchange and return nothing from a loop are recorded, not learned. That is by design and matches the slice definition in doc 01 §8.

## 6. Known limits (honest)
- These are candidates, not proofs. `MATCH` means "the same traced logic as a reference". It does not mean the program is correct.
- Aliasing, higher-order code, exceptions, macros and `loop` keywords outside the table are not modelled. The report shows them as `LIMITATIONS` or as `unsupported` facts.
- The opt-in check supports Python and C candidates only.
- The full TheAlgorithms corpus run (`learn-corpus` on 1,608 files) has not been executed here, because the checkout is not in this container. It needs the Windows run.
