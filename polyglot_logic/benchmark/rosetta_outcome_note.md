# How v3.1 outcomes are judged (written 16 Oct 2026, before outcome.py and before any v3.1 Rosetta run)

Every held-out file gets exactly one outcome, in this order of precedence:

| Outcome | When | Judged correct when |
|---|---|---|
| IDENTIFIED | the unchanged exact matcher (`cli.scan`) has a full-cover MATCH | the matched reference's source file is in `rosetta_truth.json` for the task (as in doc 07) |
| FAMILY | the family layer has an answer function | the family answer agrees with `rosetta_family_truth.json` (equal, or a prefix = broader but true), for EVERY answer path (strict) |
| LIBRARY | no traced answer, but a library call with a known family is made (`sorted`, `gcd`, `bisect`, ...) | its family agrees with `rosetta_family_truth.json` (strict) |
| NO_ALGORITHM_BODY | no loop, no recursion and no library family anywhere, and no construct the lowerers could not model | always "covered" (user decision 16 Oct); never counted as an algorithm answer, so it adds nothing to precision or recall |
| UNKNOWN | anything else, with the reason (no branch matched / unsupported construct / lowering error) | not covered |

- **coverage** = files with IDENTIFIED, FAMILY, LIBRARY, CONTAINS or NO_ALGORITHM_BODY / all files
- **precision** = correct algorithm answers (IDENTIFIED + FAMILY + LIBRARY) / those answers
- **recall** = correct algorithm answers on positive tasks / positive files

Negatives (Ackermann, Leap year, Dot product, Matrix multiplication) have no exact reference, so IDENTIFIED is always wrong for them; their FAMILY / LIBRARY answers are judged against the family truth like any other task.
The dev/test split is the one of `family_eval.py` (hash of task/language/file); test is run once.
