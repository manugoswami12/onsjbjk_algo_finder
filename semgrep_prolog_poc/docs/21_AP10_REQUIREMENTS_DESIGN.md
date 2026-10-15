# AP10 Requirements and Design (14 October 2026)

## User objective
Recognize separately labeled algorithmic logic threads embedded in the same or
interleaved Python source, while keeping AP9 fully frozen. Let Python translate
Semgrep ASTs and store reference templates, and let SWI-Prolog bind names and
trace required AST relationships. A new implementation becomes a reference through
`learn LABEL SOURCE FUNCTION`, with no new hardcoded algorithm clause.

## Nonnegotiable constraints
- Do not edit or replace any existing AP9 `.py`, `.pl`, `.cmd`, tests or facts.
- Keep Semgrep OCaml AST as the sole Python source parser for recognition.
- Keep the AP9 exact matcher and typed codec unchanged.
- No Popper, ML, Joern, CodeQL, Soufflé, NetworkX, new databases or Python AST parsing.
- Do not silently infer algorithm identity: labels are user supplied, and a
  matched reference structure is *not* proof of semantic equivalence.
- Use standard-library Python and existing SWI-Prolog only.
- Only add small, separate files. Preserve all source regions and AST operators.

## What the AP9 limitation actually is
AP9 generates terms for a function's full body or a selected AST node and
unifies them exactly. A hash assignment inserted between the loop statements
of a sorting reference makes its `Block` term differ, so a valid nested sort
may fail to match. The **AST data are already sufficient** for an initial
experiment; a full control/data-dependence graph is not required just to allow
extra unrelated statements.

## Prototype measured before implementation
A disposable Python oracle used the AP9 captured Semgrep AST fixture to form
separate sorting and rolling-update references. It allowed *ordered subsequence*
matching inside `Block` arrays only. The following outcomes were observed:

| Candidate | Sort | Hash |
|---|---|---|
| Known mixed code | YES | YES |
| Renamed mixed code | YES | YES |
| Bad loop bounds | NO | NO |
| Wrong accumulator | YES | NO |

This is a pre-implementation *Python oracle*, **not** evidence that SWI-Prolog
ran. The production matcher is written independently in SWI-Prolog.

## Minimal architecture
```
reference1.py --Semgrep--> AP9 generated Prolog reference_pattern(label1,...)
reference2.py --Semgrep--> AP9 generated Prolog reference_pattern(label2,...)
                                  | stored immutable in an AP10 catalog
unknown.py   --Semgrep--> AP9 generated candidate_pattern(...)
                                  |
                  AP10 Prolog Block-subsequence unification
                                  |
             individual THREAD matches with bound AST evidence
                                  |
          same function / exact shared target-loop-path relation
```

## Precise acceptance scope
1. **Required operators and expressions:** identical except alpha-bound local names.
2. **Required statement order:** preserved, with extra statements permitted only
   inside Semgrep OCaml `Block` lists, including nested `Block` lists.
3. **Variable consistency:** AP9 repeated local binding variables unify to the
   same target names; different reference locals must remain distinct.
4. **Algorithm identity:** user-supplied label of known implementation. The
   engine reports `AP10_THREAD` on structural match only.
5. **Composition:** a `shared_loop` result means both separate matches supplied
   the same **target AST loop path** inside one function-instance body. It does
   not imply joint execution or mathematical equivalence.
6. **New knowledge:** adding a new labeled reference does not change Prolog rules.
7. **Failure:** no match reports UNKNOWN, not absence or incorrectness.

## Explicitly out of scope for AP10
General program slicing, interprocedural alias analysis, arbitrary code motion,
mutually exclusive branch satisfiability, semantic invariant discovery,
algorithm-name inference, arbitrary unbounded graph matching and proving
zero false-positive/false-negative rates for all Python source.

## Frozen baseline and promotion rule
AP9's 102 previously successful Windows tests must remain green. AP10 is
opt-in through a *new* CMD runner and Prolog module. On this sandbox SWI-Prolog
and Semgrep are unavailable, so passing local offline tests is only a
**candidate patch**. Do not freeze AP10 until Windows full acceptance passes.
