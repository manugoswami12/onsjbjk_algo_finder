# v0.2 Lisp via ECL: logic traced in Prolog with the same rules as every other language

## 1. Requirements
| # | Requirement |
|---|---|
| R1 | Common Lisp is compiled by **ECL** to C (compile only; the program is never run). |
| R2 | The C is lowered by the **existing** AP13 C lowerer (`polyglot_logic/tools/cli.py facts_text`, tree-sitter) to language-neutral facts. |
| R3 | Logic is traced in **Prolog** by the **existing** AP13 v3 rules (`roles.pl`, `families.pl`, via `family_main.pl`), the same rules used for Python, C, Java, Rust; no text/structure matching of the source. |
| R4 | ECL specifics are absorbed by two Prolog steps only: an operator table (`ecl_op/2`, like `accessor/2` in `family_main.pl`) and loop facts from goto back edges (standard CFG natural loops). |
| R5 | A family path maps to a v0.2 branch by a table (`family_to_v02.pl`); `route_v2.pl` routes as before. |
| R6 | polyglot_logic and earlier v0.2 features are unchanged (shape witnesses `ecl_witness.py` stay as a second method). |
| R7 | Staged tests 3 -> 15 -> 55 -> 101 Lisp files; success = precision and recall >= 80 % each; keys frozen before runs. |

## 2. Design (data flow)
```
lisp file --ecl_compile--> C per defun --cli.facts_text--> neutral facts      (tree-sitter)
                                       --ecl_facts------> ecl_label/ecl_goto  (tree-sitter)
facts --swipl: ecl_main.pl--> ecl_norm.pl (ecl_op table, SSA temps, goto loops)
                           --> family_main.pl: roles.pl + families.pl  (unchanged)
                           --> family_to_v02.pl --> FAMILY|F|Name|Branch lines
branch --observed(F, learned(B), 1)--> route_v2.pl (unchanged) --> routes
```

## 3. Python pseudocode
```python
def ecl_compile(lisp_path):                     # environment: ECL
    for defun in top_level_defuns(lisp_path):   # one compile per defun: one bad form loses only itself
        yield ecl("compile-file", prelude + defun, c_file=True)

def ecl_facts(c_text):                          # facts
    lang, facts = cli.facts_text(c_file)         # AP13 neutral facts (existing)
    for fn in tree_sitter_c(c_text).functions:   # labels and gotos only
        emit ecl_label(fn, name, line); emit ecl_goto(fn, name, line)
    return facts + label_goto_facts

# ecl_norm.pl (Prolog, after load):
#   rewrite every term: call(ecl_minus,[A,B]) -> op(sub,[A,B]); call(ecl_make_fixnum,[X]) -> X;
#   call(ecl_aref_unsafe,[Q,I]) -> elem(Q,I); call_at(S, ecl_aset_unsafe,[Q,I,V]) -> assign(S, elem(Q,I), V);
#   ecl_floor2 + values[1] -> op(mod,..); runtime boilerplate statements -> dropped
#   SSA: each re-assigned temporary gets one name per definition (uses -> nearest earlier definition)
#   loops: goto at line G to label at line B < G  => loop L covering lines B..G
#          exit test: guarded goto leaving [B,G] -> loop_cond(L, not(C)); counter -> loop_var(L, X)

def identify(lisp_path):
    facts = concat(ecl_facts(c) for c in ecl_compile(lisp_path))
    for f, name, branch in swipl("ecl_main", facts):          # FAMILY lines
        observed(f, learned(branch))
    return route_v2(observed)
```

## 4. Activity types -> one program each
| Type | Program | Library |
|---|---|---|
| environment (ECL compile) | `ecl_compile.py` (reuses `ecl_filter.ecl_c`) | subprocess, ECL |
| facts (lowering + labels/gotos) | `ecl_facts.py` | AP13 `cli`, tree-sitter-language-pack |
| logic normalisation (Prolog) | `prolog/ecl_norm.pl` | SWI-Prolog |
| family tracing (Prolog) | AP13 `family_main.pl` + `prolog/ecl_main.pl` entry | SWI-Prolog |
| branch naming (Prolog) | `prolog/family_to_v02.pl` | SWI-Prolog |
| evaluation / report | `eval_ecl.py --method families` | json, argparse |

## 5. Critical logic
| Logic | Why critical | Check |
|---|---|---|
| ECL compile | environment interface | one defun per compile; missing C = UNKNOWN |
| `cli.facts_text` | interface to AP13 | unchanged program; facts printed by dump |
| SWI-Prolog call | interface | stderr = failure (env_run.swipl) |
| `ecl_op/2` normalisation | base of every role/family | unit tests per operator |
| SSA temporaries | base of copy propagation (value/3) | tests: reused T0 |
| goto loop derivation | base of steppers, gatherers, rec_class, idioms | tests: do / dotimes / while loops |
| `family_to_v02` | base of scoring | table reviewed against families.pl paths |

## 6. Problems (known before coding)
| Problem | Handling |
|---|---|
| ECL reuses temporaries (T0) | SSA rename in ecl_norm |
| Loops are goto | back-edge natural loops |
| Library macros (RUTILS `rtl:with`) | one-line shim (let*), as before |
| Comparator parameters (`funcall comp`) | ECL emits `ecl_function_dispatch`: treated as an unknown comparison call |
| Few Lisp test files for 55/101 stages | fetch more Rosetta Common Lisp tasks; keys frozen before runs |

## 7. As built
| Program | Role |
|---|---|
| `ecl_compile.py` | `ecl_units(path)`: one ECL C unit per defun (reuses `ecl_filter` reader, prelude, shim) |
| `ecl_facts.py` | tree rewriting with tree-sitter, per unit: labels -> `ecl_label(N);`, gotos -> `ecl_goto(N);`, `(ecl_floor2(a,b), values[1])` -> `ecl_rem(a,b)`, `ecl_function_dispatch(env, VV[k])(n, args) /* NAME */` -> `name(args)`, funcall of a variable -> `ecl_funcall(f, args)`; then the unchanged AP13 lowerer |
| `prolog/ecl_norm.pl` | 1 operator table; 2 symbolic execution of basic blocks (temporaries -> values, writes -> assign, or one `par_assign` when a later write reads a value replaced earlier in the block); 3 back-edge loops with `loop_cond` from the exit test and `loop_var` = tested counter stepped by a constant; 4 branch guards by control dependence (then / else of a forward conditional goto); 5 self-calls with parameter updates and the recursion loop |
| `prolog/families_v02.pl` | v0.2 branch rules over the neutral relations (AP13 unchanged): an exchange position decided by a comparison of the sequence's values -> comparison_sort / select_extreme; pair recurrence through an in-loop reaching definition |
| `prolog/family_to_v02.pl` | family path -> v0.2 branch (range accumulation: product -> factorial_like, sum -> series_sum; double recursion on n-1, n-2 -> fibonacci_like) |
| `prolog/ecl_main.pl` | loads the frozen AP12 router, AP13 `family_main.pl`, the two files above; `ecl_main`, `ecl_dump` |
| `ecl_logic.py` | `families(path)`: units -> facts -> swipl (AP13 `env_run.swipl`, stderr = failure) |
| `eval_ecl.py --method families` | same scoring and frozen key as the witness method |

Stable temporaries (one definition whose operands never change) are substituted in every block;
a temporary read in a block that does not define it and is not stable is kept as a variable.

Logic tests (`tests/test_ecl_logic.py`, own programs): 13 positives (gcd loop and tail recursion,
factorial recursive and iterative, fib, digit sum, insertion sort by rotatef with `<` and with a
comparator parameter, shift insertion sort, selection sort, binary search, max, sum) and 6 near
misses (no branch) all pass.

## 9. Fallback (separate from the normal process)
```
normal:   lisp -> ecl_compile -> ecl_facts -> ecl_main (ecl_norm, AP13 families, family_to_v02) -> answers
                                             +- ecl_export: facts after ecl_norm + answers ("earlier output")
no v0.2 branch for a unit:
fallback: earlier output -> prolog/fallback_main.pl (token stream per function, links to the file's own
          functions followed inline, depth <= 4, acyclic) -> prolog/fallback_rules.pl (DCG patterns)
```
| Program | Role |
|---|---|
| `prolog/fallback_main.pl` | reads only the exported output; `tokens//4` (a DCG) writes each result term in prefix order; `link//4` splices a linked function's tokens between `enter(G)` and `leave(G)` |
| `prolog/fallback_rules.pl` | the expandable rule base: one `fallback_pattern(Branch, Rule)//0` clause per learned pattern, each naming the case it was learned from (fold_map: dot-product-2; fold_ordered_insert: insertion-sort-1) |
| `ecl_fallback.py` | runs the fallback on the saved output; `eval_ecl_staged.py` calls it only when the normal answer is missing and tags its answers `[fallback:Rule]` |

Adding a learning: one `fallback_pattern//2` clause with its learning comment, plus a logic test.

## 10. Files without an algorithm
`ecl_main.pl no_algorithm/0`, decided from the traced facts: no defined function (top-level code only) that
either calls a function defined elsewhere (a driver) or neither loops nor recurses (a REPL transcript). The
file's output is zero (`NOCODE`); the evaluator lists it as ignored, outside precision and recall.
