# AP13: multi-language logic tracing (`polyglot_logic/`)

Learn an algorithm once from Python, then recognise the same **traced logic** in
Rust, Java, C, R, Haskell, Common Lisp or Prolog.

```
source (8 languages) ─ tree-sitter / SWI read_term ─▶ language-neutral logic facts
  ─ canon.pl (reduce variation) ─ slice.pl (trace outputs back to inputs)
  ─ evidence.pl ─▶ UNCHANGED AP12 route_extended.pl ─▶ family branch
  ─ leaf.pl ─▶ MATCH label + bindings | PARTIAL (missing relations) | UNKNOWN
```

The design is grounded in established work: program dependence graphs and
slicing, Metzger & Wen canonical forms, GRASPR/IDL-style constraint matching,
and code-as-Prolog-facts (JTransformer, SOUL). See `docs/01_*` (requirements),
`docs/02_*` (pseudocode, activities, critical logic, problems) and `docs/03_*`
(measured results).

The guarantees, as in AP2–AP12:
- Deterministic, with no ML.
- Frozen AP2–AP12 code untouched.
- UNKNOWN is preferred to guessing.
- Candidate source is never executed. The one exception is the opt-in `check` command.

Quick start: `python -m pip install -r requirements.txt`, then `RUN_AP13.cmd prefetch`,
`RUN_AP13_SELFTEST.cmd` and `RUN_AP13.cmd scan <file>`. See `docs/03_*` §5.

## Learning from the whole corpus (v2, v2.1)
```
RUN_AP13.cmd learn-dir  <TheAlgorithms/Python checkout>   # every function -> traced reference
RUN_AP13.cmd validate   <same checkout>    # drop references that match unrelated code one-way
RUN_AP13.cmd generalize <same checkout>    # common core of two variants of one algorithm
RUN_AP13.cmd validate   <same checkout>    # again, for the generalised references
RUN_AP13.cmd scan <file in any of the 8 languages>
RUN_AP13_ROSETTA.cmd --store store          # held-out measurement (Rosetta Code)
```
Design and measured results: `docs/04_*`, `docs/05_*` (v2) and `docs/07_*` (v2.1:
validation, generalisation, library folds, Windows). Library calls such as `math.gcd`
or `sorted` are reported as `LIBRARY: <algorithm>`, separately from traced matches.
