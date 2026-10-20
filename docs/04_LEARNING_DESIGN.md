# v0.2 learning: learn a new algorithm from Python only, recognise it in Python, Lisp, C and Haskell

## 1. Requirements
| # | Requirement |
|---|---|
| L1 | New algorithms (no rule knows them) are learned **only from labelled Python files** and applied to unseen **Python, Common Lisp, C, Haskell** files. Nothing is learned from the other languages. |
| L2 | Learning traces the **logic flow** (neutral facts: loops, tests, assignments, recursion, returns, links between functions), never the text or the syntax tree's shape. |
| L3 | A learned algorithm is a **Prolog DCG** clause in the form of the hand-written fallback rules, `pattern(S)` (round 2; round 1 used LCS anti-unification). It is readable and stored with its training files. |
| L4 | A learned rule must parse **no negative** training stream (Python files of other tasks); otherwise it is specialised, or no rule is kept (UNKNOWN, never a guess). |
| L5 | **Input→output fallback**: when no learned rule parses, the behaviour (AP13 io_catalog: the Prolog normal form run in SWI-Prolog, never the source) is compared with the training references, where the language has a behaviour front end. |
| L6 | Deterministic, no ML, nothing of the candidate is executed; polyglot_logic is not changed. |
| L7 | Frozen key before learning. Round 1: per test language. Round 2: staged 3/15/55/101 mixed units (held-out Python + Lisp, C, Haskell). Each needs precision and recall >= 80%, with at most 2 retries. |

## 2. Design (data flow)
```
Python training files --AP13 cli.facts_text--> neutral facts --flow tokens--> streams (label, file)
        |                                                         |
        +--> negatives: Python files of the other tasks           +--> learn_dcg.pl: covering with LGG
                                                                         -> prolog/learned_rules.pl
test file (Lisp: ECL export; C, Haskell: cli.facts_text) --> neutral facts --flow tokens-->
        phrase(learned_pattern(Label, Rule)) ; else io_catalog behaviour ; else UNKNOWN
```

## 3. Python pseudocode
```python
def streams(path):                                  # one per root function (not called by another)
    facts = neutral_facts(path)                     # same predicates in every language
    return swipl('flow_main', facts)                # tokens//4 over the logic flow, links inlined

def learn(label, positives, negatives):             # Golem-style covering with anti-unification
    rules, uncovered = [], list(positives)
    while uncovered:
        rule = uncovered[0]                         # most specific: the seed's own stream
        for e in uncovered[1:]:
            g = lgg(rule, e)                        # LCS alignment; same functor -> args anti-unified
            if not any(parses(g, n) for n in negatives) and informative(g):
                rule = g
        rules.append(rule); uncovered = [e for e in uncovered if not parses(rule, e)]
    return rules                                    # written as learned_pattern(label, k) --> ...

def apply(path):
    for stream in streams(path):
        for label, rule in learned: if parses(rule, stream): return label, rule
    return io_fallback(path) or UNKNOWN
```

## 4. Activity types → programs
| Type | Program |
|---|---|
| facts per language (environment) | `learn_facts.py` (AP13 `cli.facts_text`; Lisp via `ecl_logic.trace`) |
| logic-flow tokens (Prolog) | `prolog/flow_tokens.pl` (shared tokenizer, also used by `fallback_main.pl`) |
| learning (Prolog) | `prolog/learn_dcg.pl` (LGG of streams, covering, specificity) |
| rule store (generated Prolog) | `prolog/learned_rules.pl` |
| apply + io fallback | `learn_apply.py` |
| evaluation / report | `eval_learn.py`, `benchmark/learn_result.md` |

## 5. Critical logic
| Logic | Why critical | Check |
|---|---|---|
| neutral facts per language | interface to AP13 lowerers / ECL | same predicates; dump per language in tests |
| flow tokenizer | base of learning, applying, fallback | logic tests: equal logic in two languages gives equal streams |
| LGG of streams | base of every learned rule | unit tests on hand-written streams |
| specificity (negatives) | precision | a learned rule never parses a negative training stream |
| swipl calls | interface | stderr = failure |

## 6. Problems known before coding
| Problem | Handling |
|---|---|
| many Python variants of one task (10 N-queens) | covering: several rules per label, each specific |
| test-language idioms (Haskell equations, C loops) | one neutral fact schema; vocabulary of the tokenizer grows by general entries only |
| driver code in files (prints, tests) | only root functions that are not `<toplevel>` (unless a file has nothing else) |
| behaviour front ends missing for a language | io fallback only where AP13 io_trace has one; otherwise UNKNOWN |

## 7. Round 2: one relation, run both ways (like `sum/3`)

`sum(2,4,X)` gives 6, `sum(2,X,10)` gives 8 and `sum(X,5,20)` gives 15. One Prolog relation answers for whichever argument is unknown.

The fallback rules already have one form: the tokens of a skeleton S in order, with gaps. That form is the relation `pattern(S)//1` (`prolog/flow_tokens.pl`), and nothing else is used:

| Known | Unknown | Query | Use |
|---|---|---|---|
| S, stream | — (yes/no) | `phrase(pattern(S), Ts, _)` | apply a rule; check a negative |
| streams of one label | S | `pattern` on every stream in lockstep (`shared/2`) | learn the most specific rule |
| S | a sub-pattern G | `phrase(pattern(G), LogicTokensOfS, _)`, G shortest first, no negative holds it | the most general rule (`general/3`) |

- **Helper names.** The names of the file's own functions (link, enter, leave) are Prolog variables (AP13 G7), so unification relates the helpers of different files.
- **Quality gate.** As in AP13: at least 4 logic tokens.
- **Covering.** As in round 1 (Golem).

```python
def learn(label):
    for each uncovered file f (seed = its longest informative, specific stream):
        S = seed; for g in other files: S2 = shared([S, stream(g)]); if informative and specific: S = S2
        G = shortest sub-pattern of S's logic tokens with no negative holding it (budget), else S
        emit  learned_pattern(label, rK) --> pattern(G).
```

**Tokenizer change (retry 1).** Each linked function is spliced in once per stream. A later call is `link(G)` alone: the body is shared, as in a DAG, not re-expanded as a tree. Before this, a 40-line Python file gave a 4,987-token stream, and a stream that long holds almost any pattern.

## 8. Round 3: a learned algorithm is a new branch of the tree, at the node its logic reaches

**Requirement (user).**
- Learning is from Python only.
- The key is correct branching: broad branches give a category ("sort"), narrow ones give the algorithm ("bubble sort").
- A new algorithm is added where its logic matches the tree most closely. If the tree is A→B→C→D→E and the new program's logic follows it to C, the new branch F hangs under C: A→B→C→F.

**Why it helps.** F inherits the conditions of A, B and C. Its own condition only has to tell it apart from the other programs that reach C, not from every program: a short rule becomes safe.

**Design.**
- **The node of a function.** These are the deepest family paths of the normal process: AP13 `family_path` plus `families_v02.pl` (`deepest_families_v02/2`). They are the same for every language: Python, C and Haskell through the AP13 lowerers, Lisp through ECL. A file reaches every prefix of the paths of its functions. The root `[]` is reached by every file.
- **Learning (Python only).** The training files of a label are grouped by their deepest node. For each group:
  - C = that node;
  - the positives are the group's streams;
  - the negatives are the streams of the other training files (other labels and negatives) that also reach C;
  - F's condition is the round-2 `pattern//1` relation (shared skeleton, then the most general sub-pattern that no negative under C holds).

  The result is written as a branch clause in `prolog/learned_tree.pl`: `learned_branch(C, Label, Rule) --> pattern(S)`.
- **Applying.**
  - The file walks the tree and reaches its nodes.
  - From the deepest reached node upwards, the learned children of the node are tried on the file's streams. The first node with a matching child gives the answer (most specific first).
  - If no child matches, the answer comes from the input→output fallback; otherwise it is UNKNOWN.

**Pseudocode.**
```python
def node_and_streams(file):             # tree_main.pl: one swipl process
    facts = ecl_facts(file) if lisp else ap13_facts(file)
    load(facts); normalise                # ECL normalisation for Lisp, AP13 accessors for all
    return {deepest_family_paths(f) for f in functions}, [tokens(f) for f in root_functions]

def learn(label):
    groups = group_by(deepest_node(file), training_files(label))
    for C, files in groups:
        negs = [s for g in other_training_files if reaches(g, C) for s in streams(g)]
        for S in cover(files, negs):     # pattern//1: shared, then general
            emit learned_branch(C, label, rK) --> pattern(S)

def apply(file):
    nodes, streams = node_and_streams(file)
    for C in reached_prefixes(nodes), deepest first:
        found = {L for (C, L, R) in learned if any(parses(R, s) for s in streams)}
        if found: return found
    return io_fallback(file) or UNKNOWN
```

**Activity types → programs.**
| Type | Program |
|---|---|
| facts and node per language (environment + tree) | `learn_facts.tree()` → `prolog/tree_main.pl` (loads `ecl_main.pl`: AP12, AP13 families, `families_v02.pl`, `family_to_v02.pl`, plus `flow_main.pl`) |
| learning at a node | `prolog/learn_dcg.pl` (`reach/2` facts; negatives restricted to the node) |
| learned tree (generated) | `prolog/learned_tree.pl` |
| apply, deepest node first | `prolog/learn_apply.pl`, `learn_apply.py` |
| evaluation | `eval_learn.py --stage 3\|15\|55\|101` (frozen key `benchmark/learn_staged_truth.json`) |

**Critical logic.**
| Logic | Check |
|---|---|
| node = the normal process's deepest paths | the Lisp node equals `ecl_logic.families`; the Python node equals AP13 `family_scan` |
| negatives restricted to C | a rule under C parses no training stream of another label that reaches C |
| deepest node first | a test: a child under a deeper node wins over one at the root |

**Problems known before coding.**
| Problem | Handling |
|---|---|
| 15 of 41 Python training files reach no node (Caesar, leap year, matrix multiplication) | C = root; their rules are checked against all negatives (as in round 2) |
| files of one label at different nodes (N-queens: backtracking and sequence_query) | one group per node, each its own child |
| a test file reaching a node only through a helper function | file level: a file reaches the nodes of all its functions |

## 9. Round 3, run 3: a branch first; another rule only when a branch cannot work, by arity, never by order

**Problems** (stage 15, run 2):
1. Ackermann in C reaches `search>backtracking`. The N-queens branch learned there had an empty condition (no other Python program reached that node), so it accepted every program there.
2. Heapsort in Lisp reaches the known leaf `…>comparison_sort>heap`. The learned Levenshtein branch of an ancestor node (`sequence_query`, reached by a helper) claimed it.

**Rule (user).** Prolog is order sensitive, and more rules in one predicate keep breaking old answers, so:
- add a **branch** whenever one works;
- **only when it cannot**, add another rule. The rule must not interfere with existing ones and uses no cut.

A rule of another arity is another predicate (`p/3` for a plain sort, `p/4` for the complex ones), so it cannot change the answers of the existing ones. Its extra argument is the input→output behaviour, the project's fallback.

| Case at node C (learning, Python) | Learned | Predicate |
|---|---|---|
| a non-empty logic condition separates the file from every other training program at C (and at least one other is there: with none, any token would do, so nothing is shown) | branch | `learned_branch(C, L, R) --> pattern(S).` (`learned_branch/5` as compiled) |
| no logic condition works (no other program at C, or only the whole skeleton separates) | input→output rule | `learned_branch(C, L, R, io) :- io_equal(L).` (`learned_branch/4`) |

`io_equal(L)`: the test file's behaviour equals that of a training file of L (AP13 `io_catalog` through `compare_learners.IoCatalog`; the Prolog normal form is run, never the source).

**Applying** (`learn_apply.pl`, no cut, no first-match):
- Only the deepest node(s) the file reaches are used. Its ancestors are not: a file on a deeper known branch is not a sibling of that branch's ancestors' children.
- Every answer of both predicates there is collected (`findall`). One label is the answer; several labels give UNKNOWN; none goes to the input→output fallback over all training files.

```python
def learn_at(C, file):
    S = general(seed(file), negatives_at(C))         # shortest separating sub-pattern, or None
    emit(branch(C, label, S)) if S else emit(io_rule(C, label))   # at most one io rule per (C, label)

def apply(file):
    D = deepest(nodes(file))
    found = {L for C in D for L in branches_holding(C, streams(file)) | io_rules_holding(C, io_equal(file))}
    return found if len(found) == 1 else (UNKNOWN if found else io_fallback(file))
```

## 10. Recall over what the Python examples make learnable (user: "if you dont have examples, how can you learn")

**Learnable.** A positive test unit with expected task L is learnable iff at least one holds:
1. a learned branch of L exists at one of the unit's deepest nodes (`BRANCH_AT` from `learn_apply.pl`: the clause lookup, no matching);
2. L has a runnable Python reference (`IoCatalog.cat`) and the unit's own file has a discriminative behaviour.

Whether a rule then holds is what the test measures.

**Scoring.**
- Recall is taken over the learnable positives.
- Precision is taken over every answer, including those on negatives and on positives that are not learnable.
- Not-learnable positives are listed, and the full-key recall is printed beside it.
- The learner is not changed.

## 11. Augmented Python examples (user: augment where the algorithms are not learnable)

Where the Rosetta Python files of a task gave no usable example, I wrote one plain textbook Python version of the algorithm (loops and arithmetic, no library shortcut), in `benchmark/learn_augment/`, labelled in `benchmark/learn_augment.json`. The test files are not read for this.

| Task | Why the Rosetta Python files gave nothing | Augmented example |
|---|---|---|
| Ackermann | recursive form only (reaches `numeric`), no runnable reference | the tail call written as a loop |
| Caesar | `str.translate` / `maketrans`, `dict(zip(...))` | the shift by character arithmetic |
| Knapsack 0-1 | no runnable reference, no table form | the (items+1) x (capacity+1) DP table |
| Matrix multiplication | `map` / `zip` / `sum` forms | three nested loops |
| Run-length | its branch does not hold for loop-based code | scan of runs of equal characters |

They are training files only: learning stays Python only, and the frozen staged key is unchanged.

## 12. Uniform conversion: the same component gives the same Prolog term in every language

Test: `tests/test_uniform.py`. The same algorithm with the same structure in two languages must give the same tree node and the same tokens (`tests/data/uniform/`). Fixes, each in the shared conversion and each reusing an existing table or role:

| Component | Was | Now | Where |
|---|---|---|---|
| library call (char-code / chr / ...) | ECL kept `cl_char_code` | AP13's `lang_tables.SYNONYMS` applied to ECL names (`lib_synonym/2` facts), last in the ECL table; a variadic argument count is dropped | `ecl_facts.lisp_synonyms`, `ecl_norm.pl` `lisp_library/2` |
| order comparison | `cmp(lt/le/gt/ge)` | one `cmp(order)` (a > b is b < a; skip-if-greater is take-if-not-greater), as AP13 canon.pl normalises direction and negation | `flow_tokens.pl` |
| counting loop | C: `i = 0`, `i++` statements; ECL: explicit counter; Python: `range` call | the counter's constant start and step (AP13 `stepper` role) and the `range` it runs over belong to the `loop` token | `flow_tokens.pl` `counter_step/3`, `loop_source/2` |
| nested call | Python lists `chr(ord(c))` inside `append(...)` again as statements | a call inside another expression of the same statement is not a statement | `flow_tokens.pl` `nested_call/3` |
| `loop ... collect` | ECL's head cell, tail cursor copy, dead temporary | the existing collect rewrite sees through the cursor copy; dead compiler temporaries are removed | `ecl_norm.pl` `cursor_of/3`, `dead_temporaries/3` |
| append | Lisp `collect` | `call(append)` | `flow_tokens.pl` |
| 2-D array write | ECL row-major `c[i*dim+j]` on the write target | normalised like a read: `elem(elem(c,i),j)` (so AP13 `table_fill` sees it) | `ecl_norm.pl` write step |
| new array | `si_make_pure_array` / `[[0]*n for ...]` | one `new_array` token | `flow_tokens.pl` `new_array/1` |

Also corrected: the ambiguity check counts every learned label that holds (known tasks' too), as the design says; it had counted only the 12 new labels.

## 13. Siblings at one node: the label is computed, not blocked (user: sum(2,4,X))

**Run 8 (replaced).** Each clause excluded its siblings' marks (`\+ any_of(Marks)`). With one training file per sibling, the marks were common tokens, so correct answers were blocked.

**Now.** The label is the computed argument, as X in `sum(2,X,10)`. Every clause stores its example (`learned_ref(C, L, R, LogicTokens)`, the logic tokens of its file's most specific stream).
- When the clauses that hold at the deepest node give more than one label, each is scored by `shared([Example, FileLogic], G)`. This is the reversible `pattern` relation with the shared part unbound, run on both. The score is `|G| / |Example|`; an input->output rule scores 1.0 (equal behaviour).
- The closest label stays. A tie stays ambiguous (UNKNOWN).

```prolog
closeness(C, L, R, Streams, Sc) :- learned_ref(C, L, R, Ref), ..., shared([Ref, Ls], G), length(G, K), Sc is K / |Ref|.
```

## 14. Token-based learning removed (user: "clear the token nonsense"; the method is not probabilistic)

Sections 3 (pseudocode of rounds 1-2), 7, 8 (the branch condition), 9 (the branch case), 12 (the token rows) and 13 are superseded. Learned conditions were subsequences of logic-flow tokens, and in run 9 a share of matched tokens. That is not logic tracing, and it was my design, not the method.

Removed:
- `prolog/learn_dcg.pl`, `prolog/flow_main.pl`, `prolog/learned_rules.pl`, the token parts of `tree_main.pl` and `learn_apply.pl`;
- the learning predicates of `flow_tokens.pl` (`pattern//1`, `shared/2`, closeness).

Learning is now only the two deterministic parts of the method:
- **Logic.** The tree node the Python file reaches: the normal process's relations (AP12, AP13 families, `families_v02.pl`), `prolog/tree_main.pl`.
- **Input->output.** The branch at that node holds where a file there has the label's behaviour: `learned_branch(C, L, io, io) :- io_equal(L).` (`prolog/learn_tree.pl`).

Applying uses the deepest node(s), collects all answers (findall), and gives UNKNOWN for several labels.

Kept from section 12, since they are conversions of facts, not tokens: the AP13 synonyms for ECL names, the collect rewrite through the cursor copy, dead compiler temporaries, and the 2-D write target. `tests/test_uniform.py` now compares tree nodes.

`flow_tokens.pl` remains only for the separate Lisp fallback of doc 03 section 9 (a DCG over the normal output, as asked then).

## 15. Built branches (user: "if C is different and we can't learn it, we build the code")

Where the Python examples cannot teach an algorithm in another language, a branch is written by hand in the normal tree, the way the original repo's branches are (`family_to_v02.pl`, `families_v02.pl`). Each such branch:
- states the logic as relations over the facts, the same in every language;
- names the case it was built from;
- has a logic test on own programs, with negatives.

`eval_learn.py` takes a built branch's answer first (tag `built:`).

| Branch | Logic (relations) | Built from | Logic test (`tests/test_uniform.py`) |
|---|---|---|---|
| `towers_of_hanoi` under `numeric>recurrence>double_recursion` | Two recursive calls, each on n - 1, made one after the other for their effect only: their results are discarded (AP13 `rec_class(double_recursion, F)`, the sequential form). For Lisp, ECL's tail jump sets n to n - 1 in its own statement. It extends the existing clause: fibonacci_like first, then towers_of_hanoi, else recursive_decomposition. | towers-of-hanoi-1.c | hanoi .py/.c/.lisp → towers_of_hanoi. Negatives: fib → fibonacci_like; in-order walk → recursive_decomposition; Ackermann (its jump sets n to 1); an edit distance (call results used) |

### 15b. Built branches and front-end fixes (stages 15 and 55)

Built branches (`families_v02.pl` relations, `family_to_v02.pl` branches; logic tests in `tests/test_uniform.py`):

| Task | Node | Relation (every language) |
|---|---|---|
| ackermann | numeric>recurrence>nested_recursion | `f(m-1, f(m, n-1))`: a self-call inside the argument of a self-call that counts the first parameter down (Lisp: the tail jump's update is the inner call) |
| knapsack_01 | marking>table_fill>capacity_reduction | a cell from the previous row at a capacity reduced by a non-constant amount, `T[i-1][j - w]` |
| caesar_cipher | sequence_transformation>elementwise_map>alphabet_rotation | `chr((code(c) - b + k) mod 26 + b)` with one non-literal character code (Vigenere has two); the Haskell point-free form |
| matrix_multiplication | sequence_transformation>construction>matrix_product | the accumulated `a[r][k] * b[k][c]` (or `col(b, c)[k]`); the functional form, rows mapped to `(apply #'mapcar dot b)` |
| run_length_encoding | sequence_transformation>construction>run_length (AP13's node) | a group extended while the element equals its first, else emitted and restarted |
| n_queens | search>permutation_filter, search>diagonal_conflict | the permutations with distinct `x_i + i` and `x_i - i`; the sum and the difference of the same positions used as keys (membership or occupancy index); the bit-mask diagonals shifted left and right |
| lcs | sequence_query>two_sequence_match>longest_common | on a match the diagonal + 1 (or the element in front), else the larger of the two one-sided steps |
| levenshtein | sequence_query>two_sequence_match>edit_distance | a min with at least two +1 alternatives; or, by recursion, the diagonal unchanged on a match and +1 otherwise |
| roman_encode | library>roman_numerals | Lisp `format` with the `~@R` directive (AP13 doc 07: a library call names its algorithm) |
| josephus | numeric>recurrence>josephus_recurrence (AP13's node) | AP13's own relation, mapped |

Front-end fixes found while building (each the same component as the same term):
- C: the file's own macros are expanded by `cpp` (without system headers); a row-major index `q[r*d + c]` with a non-constant stride is `q[r][c]`, as ECL's.
- ECL: a `&key` comparator that defaults to an equality predicate is `=`; the file's own `defmacro` is defined before its uses compile; a call of the function's own name is `$self`; VV string constants keep their text (`str(...)`).
- No-algorithm files in every language: a source that defines nothing (a REPL transcript) gives zero. For Haskell this is decided from the tree-sitter tree, since AP13's lowerer gives no facts for some definitions too.

## 16. Front ends extended where AP13's lowerers drop a component (user: extend the Haskell lowering)

AP13's lowerers are unchanged. v0.2 subclasses them, as AP13 v4 subclassed its imperative lowerer, and adds only what they leave out. `learn_facts.tree_facts` uses the subclasses for the learning test.

**`haskell_logic.HaskellLowerer`** (subclass of `lower_equations.Lowerer`):
- Definitions inside a parse `ERROR` (tree-sitter keeps the valid subtree) are lowered.
- A bind with a where block: its functions are lowered. `f = memoize g` / `f = g` makes `f` an alias of `g` (a memo wrapper is the function it wraps).
- An infix definition ``q `f` qs = ...`` gets its name and parameters.
- Tuple patterns in heads, where binds and generators.
- Several generators are nested maps; `(a, b) <- xs `zip` ys` binds the elements of both sequences in lockstep.
- `x ! (i, k)` is `elem(elem(x, i), k)`; `f a $ b` is `f a b`.
- `if/then/else` and `let ... in` in a result.
- Sections `(x ==)`, lambdas, `(-)` as a value (`fn(sub)`), tuples (`tuple([...])`, as AP13's Python lowerer writes them).
- A top-level point-free bind is a function of no parameters.
- `fromIntegral` and the other numeric conversions keep the value.
- The source is dedented first.

**`imperative_logic.ImperativeLowerer`** (subclass of `lower_imperative.Lowerer`, used for Python and C):
- An assignment used as a value (`a = b = e`, `(y = f(x)) < x`) is its value.
- A Python slice is `call(slice, [s, i, j])`.
- A field is `field(obj, name)` (AP13: `other(field)`).

**Python REPL sessions** (`>>> def j(n, k): ...`): the program is the session with its prompts removed (`learn_facts.session_facts`).

**Built branches added for stage 101** (logic tests in `tests/test_uniform.py`):
- **Ackermann**, tightened: the inner call keeps `m` and counts another parameter down; Hanoi with an accumulator counts the same one.
- **Hanoi**, functional and accumulator forms, and the nested form at `double_recursion`.
- **Edit distance:** the match path adds nothing (LCS adds 1); the returned forms.
- **LCS:** the pair form `(seq, len)`; the larger result chosen by any comparison.
- **Run-length:** `span (x ==)` and `group` with the length of each group.
- **N-queens:** zipWith-shifted membership, the sum and difference equality form, loop conditions.
- **Caesar:** the base added back is not a shifted code; the `maketrans` rotation table.
- **Josephus:** elimination modulo the number left.
- **Leap year:** divisibility by 4, 100 and 400, or the masks 3 and 15.
- **Roman:** a greedy table walk emitting another part of the same entry.

## 17. All of TheAlgorithms/Python: learn each algorithm, test it, write a rule by hand where learning fails

User: "complete all thealgorithms/python and first try to learn each algorithm, test it if learnt correctly, if not
write rule by hand, also maintain a text prompt style data ... one or two rules will work". And: "dont be overconfident".

### 17.1 Design
- Corpus: TheAlgorithms/Python at AP13's pinned commit `e1a2a8b0` (1,608 files). It is cloned outside the repo and never
  edited.
- Labels: one label per file stem; `project_euler/problem_NNN/solK.py` takes the label `problem_NNN`. Package and test
  files carry none. This gives 1,346 labelled files and 1,288 labels.
- Groups: the files that AP13's frozen key (`polyglot_logic/benchmark/rosetta_truth.json`) maps to one Rosetta task share
  that task as their group, e.g. bubble_sort and bubble_sort_recursive. The key is not changed: pigeonhole_sort is not
  in the Counting-sort group, so a pigeonhole file answered `counting_sort` counts against it.
- Learning (Python only, the learner of section 14):
  - `learned_branch(Node, L, io, io) :- io_equal(L)`;
  - two more specific branches at the same node, from the original repo's own machinery:
    - `trace`: the same writes to input positions in the same order (AP13 io_trace);
    - `logic`: an AP13 learn-dir reference of the label's training file matches (exact traced logic, subsumption).
- Answer: the most specific evidence that names anything decides. The order is a built or hand branch, then
  trace/logic, then io at the node, then io alone. Several groups give UNKNOWN; there is no cut, and clause order
  decides nothing.
- Tests per label (`eval_ta.py --status`):
  - T1 self: its own file is answered with its group. This is weak, because the file's own behaviour is in the catalog.
  - T2 confusion: no file of another group is answered with its group.
  - T3 held-out: the Rosetta files (Python, C, Common Lisp, Haskell) of its task are answered with its group. Only the
    labels mapped to a Rosetta task have this test.
- Statuses:
  - learned_heldout: T1, T2 and T3 pass;
  - learned_self: T1 and T2 pass, with no held-out file;
  - hand_rule: the tests pass with a hand rule answering;
  - not_learned, with its failure kinds.
- Hand rules: `prolog/ta_rules.pl`, `hand_branch(Node, F, Label)`.
  - They are relations over the language-neutral facts, the same in every language.
  - The family tree and its branches are unchanged, so the earlier keys keep their answers.
  - A file's hand answer is the labels of its functions that no function with a label of its own calls. A partition
    helper belongs to its quicksort, and a caller combining two different sorts (an introsort) makes its helpers parts.
- Prompts: `docs/HAND_RULE_PROMPTS.md` holds one reusable prompt per failure kind. `benchmark/hand_rule_prompts.jsonl`
  holds the filled-in prompt of every label that was not learned.

### 17.2 Pseudocode
```python
labels = {rel: stem(rel) for rel in corpus if labelled(rel)}
learn(labels)                                   # learned_branch/4 at each file's deepest node: io, trace, logic
for f in corpus + rosetta_files_of_mapped_tasks:
    nodes, learned, normal, hand = apply(f, io_equal, io_trace_equal, logic_equal)
    answer[f] = first non-empty of (built | hand, learned trace/logic, learned io, io) -> one group, else UNKNOWN
for label in labels:
    T1 = all(answer[f] == group(label) for f in files(label))
    T2 = [f for f in corpus if answer[f] == group(label) and group(labels[f]) != group(label)]
    T3 = [(f, answer[f]) for f in rosetta_files(task(label))]
    status[label] = ...; prompt[label] = KIND_PROMPTS[kind].format(...) for the failures
```

### 17.3 Activity types
| Activity | Program |
|---|---|
| corpus labels, groups | `ta_corpus.py` |
| learn, answer, test, status, prompts | `eval_ta.py` (`--learn`, `--run`, `--heldout`, `--status`) |
| learned branches | `prolog/learn_tree.pl` (io, trace, logic), `prolog/learn_apply.pl` |
| hand rules | `prolog/ta_rules.pl` |
| facts the rules need | `imperative_logic.py`: `loop_step/2` (Python range step, C for update; a constant or a variable stride), slice steps (`s[::-1]`) |
| logic tests | `tests/test_uniform.py` `HandRuleTests`: own programs (Python, C, Lisp), positives and close negatives, and a clean load of the rules |

### 17.4 Critical logic
| Point | How it is kept |
|---|---|
| a label counts as learned only when tested | T1 is reported as weak; T2 runs over the whole corpus; T3 uses held-out files written by other people, in four languages |
| no rule loosened to fit one file | every rule has a close negative: bubble/rotate-once, gnome/pass helper, Fibonacci/Lucas and Pell, factorial/double factorial, gcd/extended gcd, primality/factorisation, digit sum/number reversal, counting/word count, binary search/binary insertion sort |
| same component, same term | e.g. a swap is `exchange/4` whatever its spelling (tuple swap, temp, `rotatef`, swap macro), and a counting loop is `range(...)`, a C `for`, a Lisp `loop for`, or a Haskell `[1..n]` fold |
| runs never mix rule versions | a run copies the working tree to a snapshot and runs there (an edit during run 2 broke 62 of its files: that run was discarded) |

### 17.5 File rules: every TheAlgorithms/Python file identified (user: "forget generalizing, hand write all the failed rules")
The aim changed: every corpus file must be answered with its own label. Generalising to other code is no longer the
aim for this tier. The file rules are deliberately specific. They identify the corpus and are not general
recognisers; the general relations (17.1, `ta_rules.pl`) and the learned branches stay as they were.

- **Tiers:** `hand_specific(F, Label)` in `prolog/ta_file_rules.pl` is a tier before the general hand rules and the
  learned branches. `eval_ta.decide` takes the first tier that names anything; several labels in one tier is UNKNOWN.
  A sieve inside an Euler file is therefore that Euler problem: its file rule wins over the sieve rule.
- **Component:** a statement's relation (AP13 `rel_of/2`) or a call it makes, with locals renamed `v`, parameters by
  position `p(K)` and the file's own functions `fn` (`prolog/ta_signature.pl`). The same component in other spellings
  gives the same term.
- **Writing a rule:** `ta_distinct.py --propose LABEL` lists, in this order of preference:
  - a component no file of another label has;
  - a pair that together occur only in the label's files;
  - a component with exclusions (`\+ file_has(C)` for a component of each other file that has it).

  The ranking prefers the algorithm's logic on its inputs over reading input, printing, timing, tests and input
  checks. `--write` regenerates the proposed section for the labels of `benchmark/ta_file_rule_labels.json`. The
  proposals were reviewed per folder, and the ranking was corrected where they named noise, e.g. a `main()` input
  read for a1z26 became `ord(c) - 96`.
- **Checking:** `eval_ta.py --rehand` recomputes the built, hand and file-rule evidence of every file and keeps the
  run's learned evidence. `--status` then gives T1 and T2. A rule is about 3 s per file: the file's components are
  abstracted once per run.
- **Front-end gaps found on the way** (fixed in `imperative_logic.py`; the same component gives the same term):
  - `f(x for x in s)`: the generator was lowered as its parts;
  - dict literals;
  - f-string interpolations (`f"{a | b}"` vs `f"{a ^ b}"`);
  - chained assignments.
- **What no logic separates:** TheAlgorithms itself holds identical copies, `ciphers/base58.py` = `ciphers/base64_cipher.py`
  and `maths/base_neg2_conversion.py` = `conversions/int_to_negative_binary_base.py`. Two web scripts have all their
  code under `if __name__ == "__main__":`, which AP13 does not lower.

### 17.6 Result (run 9 answers, the hand, built and file-rule evidence re-decided on the final rules)

**Corpus:** 1,283 of 1,288 labels pass T1 (every file answered with its own label) and T2 (no other file is):
- learned: 709, of which 5 have a held-out test;
- general hand rules: 56;
- file rules: 501;
- labels whose own files pass but whose Rosetta files are not all recognised (T3 only): 17.

These 17 are counted among the 22 not learned in `ta_result.md`. The 5 that fail T1 cannot be separated by logic:
- two identical copies inside the corpus (base58 = base64_cipher, int_to_negative_binary_base = base_neg2_conversion);
- two scripts with all their code under `__main__`.

**File rules on other people's code:** they never fire, because `same_file/1` requires every component of the
label's file. With a 60% overlap, small Euler files had matched Rosetta Fibonacci and sieve programs, and held-out
precision fell to 69.9%. That version was replaced.

**Held-out Rosetta files (450, unseen code):**

| | correct | wrong | UNKNOWN | precision | recall |
|---|---|---|---|---|---|
| all evidence | 158 | 10 | 282 | 94.0% | 35.1% |
| learning alone | 31 | 16 | 403 | 66.0% | 6.9% |

**Stage 101 (round 2 test):** 40/40 precision, 81.6% full-key recall, unchanged.

**Prompts:**
- `benchmark/rule_prompts.jsonl` and `docs/RULE_PROMPTS.md`: one prompt per rule written (501 file rules,
  51 general relations), with the clauses produced;
- `docs/HAND_RULE_PROMPTS.md` and `benchmark/hand_rule_prompts.jsonl`: one prompt per label still failing;
- `docs/HAND_RULES_WRITTEN.md`: worked examples.

## 18. Separate fallback for new code, and the final report (kept out of the pipeline)

Everything in this section is separate from the pipeline. No pipeline file loads it, and no pipeline answer changes.

- **Class relations** (prolog/class_specs.pl, sum(2,3,X) style). A file is a *new version of a known class* when every
  root function (prolog/call_roots.pl) runs on every battery input and satisfies one class relation. A second witness
  is required: the file reaches a tree node. Result: 39/39 held-out decisions right, 37/37 TheAlgorithms claims
  right.
- **New algorithm.** It cannot be told from an incorrect implementation, so it is answered "new or incorrect
  implementation", and no rule is created from it.
- **Proposed branches** (tools_manual/write_branches.py -> prolog/proposed_branches.pl). Each TheAlgorithms class
  decision becomes `proposed_branch(Node, Class) :- class_holds(Class).` at the nodes its file reaches below a root.
  On the held-out files they fired 14 times, right 14 times. On TheAlgorithms (leave-one-out) they fired 25 times,
  right 25 times.
- **Library names** (prolog/library_names.pl). A file whose whole computation is one library call is named by that
  call: 3 held-out files, 0 wrong.
- **v0.3 runner** (pnf_v03.py, prolog/interp_v03.pl). It extends AP13's lowerer and interpreter without editing
  them: lambdas and closures, module-level constants, generator arguments, more library relations.
- **The user's rule for the rest.** A file that reaches a node but matches no rule is a variation of the family at
  that node; a file that reaches no node is an error or a new class.
- **Reporting criteria (final_report.py -> benchmark/FINAL_REPORT.md).** Bad code is ignored:
  - a held-out file is *not analysable* when the pipeline gave it no answer and no root function runs on every
    input;
  - a TheAlgorithms file is not analysable when it has no algorithm code;
  - files with identical logic are one alias group;
  - wrong answers are never excluded, and the all-files numbers are reported beside the analysable ones.
- **Measured and not built:** a class veto of the pipeline's wrong answers. It fixes none, and its looser form would
  turn 15 correct specific answers into a class name.

## 19. Tracing the code's logic: conversion fixes, each tested against all data (user: "all these are due to bad tracing of code logic")

**Rule (user).** The remaining wrong answers come from converting code to Prolog wrongly, not from the tree. Each
conversion fix is a rule of the language, never of an algorithm. It goes in alone and is checked against all existing
data: the nodes of all 1346 TheAlgorithms and 450 held-out files, then relearning and full runs. A change is dropped
if one problem occurs that the idea itself cannot fix. A file that worked before and breaks is checked once: its
generated parts (learned branches, fingerprints) are regenerated; a hand rule is never rewritten silently.

**19.1 A returned value traced through the variable that holds a recursive call** (`prolog/trace_returns.pl`, called
by `tree_main.pl` `tree_load/2`). AP13's copy propagation replaces only a variable with one definition, so
`lesser = f(lesser); ...; return lesser + equal + greater` and `z = 1; if n > 1: z = n * f(n - 1); return z` were not
traced to the recursive calls. Two value-flow shapes, by line order and guards: the last definition holds on every
path to the return (substituted), or a default plus one guarded override (two guarded returns, as a conditional return
is). Only values holding a recursive call, only when the variable is read nowhere but in the return; the call's facts
(the call and its parameter updates) move with its value.

| Check | Result |
|---|---|
| hand check | factorial-7.py reaches `range_accumulation`, as TheAlgorithms' factorial does; quicksort-1.py traced but still `sequence_query` (list `+` is not `concat`: another idea) |
| fault found, fixed within the idea | red_black_tree's `black_height` lost `double_recursion`: its variables are also tested (`left != right`); now traced only when the return is the variable's only use |
| nodes, all 1796 files | 2 change: factorial-7.py and binary_search_tree.py (`inorder`, `postorder`: default `[]` and the guarded join, now traced) |
| relearn + full runs | first run: 3 learnt files lost (segment_tree, lazy_segment_tree, wavelet_tree): their file rules' fingerprint (`same_file/1`, generated from the facts) held the untraced returns. Fingerprints regenerated from the current facts (`ta_signatures.json` -> `ta_file_components.pl`; `ta_file_rules.pl` unchanged): learnt 1344/1344, 0 differences; new code 158/10 -> 159/9 (factorial-7.py: problem_020 -> Factorial) |

**19.2 A Haskell recursion ends at its base cases** (`haskell_logic.py` `base_case_conditions`). AP13's equational
lowerer derives the recursion's loop condition only from a `|` guard of variables, so `go acc 0 = acc; go acc n =
go (acc * n) (n - 1)` had none and the accumulation rule (an update guarded only by the continuation) could not hold.
As AP13's shared post-pass does for the other languages, every return without a self-call gives `not(guard)`; a guard
the self-call steps also carry is context, not a base case.

| Check | Result |
|---|---|
| hand check | factorial-8.hs reaches `range_accumulation`; gcd, fib and hanoi Haskell files keep their nodes |
| nodes, 157 Haskell files (TheAlgorithms is Python: its facts cannot change) | 2 change: factorial-8.hs, and `adjust` in sieve-of-eratosthenes-16.hs (numeric -> sequence_query: AP13 nests a called local function under its caller's loop and both name an unnamed parameter `$arg0`; a separate lowering fix, no answer changed) |
| 450 held-out files | 1 answer changes: factorial-8.hs problem_020 -> UNKNOWN; new code 8 wrong, precision 95.6% |

**19.4 Two behaviour-lowering fixes switched on** (`lowering_v03.py`, installed by `crosslang_frontends.install`): the
Lisp loop's `finally` runs once after the loop (it ran inside the body: fib(n) = 1, signum's behaviour), and C/Java
`x op= y` keeps its operator (`result *= i` was `result = i`).

| Check | Result |
|---|---|
| behaviour normal forms, all 2102 files | 28 change, all Rosetta C or Lisp programs with `x op= y` or `finally`; no TheAlgorithms normal form changes, so the catalog and learnt answers cannot change |
| 450 held-out files | 1 answer changes: fibonacci-sequence-9.lisp signum -> Fibonacci-sequence (factorial-2.c now computes n!, still named problem_020 by the exact-trace tier) |
| class fallback recomputed | primality-by-trial-division-2.c now runs (prime_check); sum-digits.c now runs (no class: its base argument); towers-of-hanoi-1.py undecided (it only prints; the same with the old code) |

New code: 7 wrong, precision 96.2%, recall 85.0%.

**19.5 Dropped: `+` on lists as concatenation.** In a function, an `add` with an operand known to be a list (a list
literal, a concat, a variable created as a list) was read as `concat`, the form `[*a, *b]` already lowers to. The
conversion is right (quicksort-1.py and -3.py reached `partition_recursive` and were answered Quicksort), but AP13's
partition idiom accepts any concat of two recursive results as a partition sort, with no test that the parts were
split by a comparison with a pivot. Correctly converted joins then became sorts: towers-of-hanoi-2.py and -3.py and
TheAlgorithms' huffman.py were answered Quicksort, and inorder_tree_traversal_2022, problem_109 and counting-sort-1
lost their answers. A fault of the tree's rule, not of this conversion: dropped under the rule. The next idea is the
partition rule itself: the parts must be filtered by comparing elements with a pivot.

**19.6 The user's split of the remaining 7.** 1 (quicksort-1) and 2 (insertion-sort-3): tree-sitter gives no more
information (that `+` joins lists); no Python reverse engineering, other parsers only tested on the side. 3, 6, 7:
solve. 4, 5: hand-test combinations first.

| Case | Change | Result |
|---|---|---|
| 3 factorial-2.c -> problem_020 | accumulation rule: a guard every enclosing loop has (C's `if (n < 0) return -1;`, Python raises instead) does not condition the update; first version (any enclosing loop) took two sieves and lost problem_124, fixed within the idea | adopted: learnt 0 differences; problem_020 -> Factorial |
| 7 roman-2 -> magicdiamondpattern | an AP13 exact-logic match is dropped when behaviour contradicts it (every function of the match computes outputs, the matched function none; or both compute and differ); faults fixed within the idea: compare's no-verdict is no contradiction (bucket_sort), a match spanning a running helper is not contradicted (expected_shortfall) | adopted: learnt 0 differences; magicdiamondpattern -> UNKNOWN |
| 2 insertion-sort-3 -> average_mode | `q[:] = E` read as a write of q (and q the output) | dropped: became Cycle-sort (still wrong), rotate_matrix and haralick_descriptors lost |
| 6 perfect-numbers-1 -> primelib | a match on a root of a file whose roots compute different things names nothing | dropped: 9 learnt answers lost or wrong (volume.py, rotate_bits.py: several functions of one topic look the same as a library) |
| 4 lcm-2, 5 levenshtein-5 | hand-tested, not built: `def f(x): return lambda y: E` as f(x, y) in (a) the structure facts, (b) the behaviour form, (c) both, (d) any statements before the return | (b)/(c): lcm computes exactly TheAlgorithms' LCM (36, 35, 0, 42, 300), but the hand-built gcd branch at the helper gcd_.go's node decides first (built tier before io); (d) uncurries levenshtein, whose body is reduce/scanl with functions as values, which AP13's interpreter cannot evaluate |

New code after 19.6: 5 wrong (quicksort-1, insertion-sort-3, lcm-2, levenshtein-5, perfect-numbers-1).

**19.7 Python tells about its own programs (cases 1 and 2).** User: "use python to answer about its own programs".
Tree-sitter stays the parser; Python's own ast (static, the program is never run) adds facts beside its facts for a
`.py` file (pyast_facts.py, called by learn_facts.tree_facts): `list_var(F, X)` (every assignment of X in F, annotated
ones included, gives a list, or X is appended to), `list_param(F, P)` (P is sliced), `list_func(F)` (every return
gives a list; a fixed point over the file's functions). Three rules use them, each a rule of the language:

| Rule | What it does | Faults met, fixed inside the idea |
|---|---|---|
| prolog/ast_concat.pl (after trace_returns) | an add with a list operand is concat, flattened (as `[*a, *b]` lowers) | facts of one predicate written apart (34 files failed to load); annotated assignments not read (problem_109) |
| families_v02.pl partition_evidence/1 | for a join Python made concat, `partition_recursive` holds only when two recursive results are joined on parts split by a comparison (appended under one, or filtered by one), or AP13's exchange loop partitions; otherwise the node falls back to `[sequence_transformation]` | `ac_joined/1` undefined on the Lisp path; Hanoi's moves and huffman stay `double_recursion` |
| prolog/slice_write.pl (before trace_returns) | `q[:] = E` of a parameter, in a function that returns nothing, is a write of q with value E and q is its output | applied to every function, rotate_matrix's reverse_column (which returns the matrix) lost its node |

Two hand terms quoted the old wrong reading of a list join and were restated in the corrected form, the rules
unchanged: problem_109's file rule (`singles + doubles + triples + [0]` is `concat([v, v, v, [0]])`), and the LCS
built branch's "matched element put in front" (`[x] + lcs(...)` is also accepted as `concat([list([_]), D])`; found
by tests/test_uniform, no file of the data changes node).

Checked against all data: tree nodes of 2102 files (14 changed, each explained: quicksort-1, -2, -3, -6 and
TheAlgorithms' three_way_radix_quicksort reach `partition_recursive`; returns that join lists become sequence
transformations: merge, merge_sort, to_title_case; insertion-sort-3 reaches `sequence_transformation`; a few one-level
nodes the add had made go away), relearnt, fingerprints re-indexed, `--run` and `--heldout`: learnt 1344/1344 with 0
differences. New code: quicksort-1 Cycle-sort -> Quicksort, quicksort-3 UNKNOWN -> Quicksort, insertion-sort-3
average_mode -> UNKNOWN (Insertion, Merge and Pancake sort hold alike at its node). 177 correct, 3 wrong, precision
98.3%, recall 85.9%. Remaining wrong: lcm-2, levenshtein-5, perfect-numbers-1.hs (19.6).

**19.8 A function that returns a function (cases lcm-2, levenshtein-5).** User: "first ensure our code can
differentiate whether a function returns a variable or a function; if it returns a function, recurse exactly the way
we deal with a new function". Built by hand first (scratch), then in the code; each a rule of the language:

| Part | Rule | Why it was needed |
|---|---|---|
| returns_function.py (both lowerings) | a function whose every own return gives a lambda (same parameters) is the new function f(x, y): the lambda's parameters follow, its expression is the return (repeat for lambda in lambda); `h(a)(b)` of such a function of the file is `h(a, b)` | lcm(x) returned lambda y: ...; nothing of it was read |
| behaviour_v04.py lift | a nested function is a new function: the variables it reads from its enclosing function become trailing parameters; inside, `g(a)` is `A.g(a, free...)` and `g` as a value the closure `lambda(params, A.g(...))`; names resolve lexically | levenshtein's go reads s1 and is passed to reduce |
| behaviour_v04.py kinds | a parameter passed to list(), zip(), enumerate(), sorted(), reversed(), set() or tuple() is a sequence | `list(sa)` made sa an int on the battery |
| prolog/interp_v04.pl (main behaviour tier) | zip/min/max of any arity, itertools.accumulate, functools.reduce (interp_v03's reduce failed: a foldl/6 call with a state pair), a boolean in + - * as 0 or 1; each clause only where interp.pl throws | TheAlgorithms' levenshtein_distance adds `(c1 != c2)`: it now runs on every input (was 2 of 5) |
| eval_ta.helper_functions | a function called (directly or through others) by one whose own behaviour names labels, none of which its evidence (behaviour, built and hand branches at its node, exact-logic matches) names, is that function's step: its evidence does not name the file (learn_apply.pl prints the evidence per function and the calls) | the gcd branch on lcm's helper gcd_.go decided first |

Hand test, then all data (2102 files: only held-out files with such functions change node, the uncurried functions
reaching one-level nodes; relearnt, re-indexed, --run, --heldout): learnt 1344/1344, 0 differences. New code:
lcm-2 gcd -> Least-common-multiple, levenshtein-5 problem_007 -> Levenshtein-distance, and gained
levenshtein-distance-1.py, -2.py, -2.hs and perfect-numbers-4.py. 183 correct, 1 wrong (perfect-numbers-1.hs ->
primelib), precision 99.5%, recall 88.0% of 208.

**19.9 perfect-numbers-1.hs -> primelib (tried, dropped).** The trace through the tree: the file reaches
`numeric>divisor_test`, where the perfect_number branch (learned from maths/perfect_number.py and
special_numbers/perfect_number.py) never holds: both TheAlgorithms files compute nothing on the battery, because a
generator as a call's only argument (`sum(i for i in range(...) if n % i == 0)`) lowers wrongly in the main behaviour
lowering. primelib, a mixed file, has its label only at its deepest node (its factorial's); the Haskell function
reaches it only through the behaviour-only tier. Tried: (a) the generator as one comprehension, (b) an input check
(leading `if p <op> k: return K` in a non-recursive function: that input no evidence), so that the node's branch
holds (perfect-numbers-1.hs -> Perfect-numbers by hand). All data: is_power_of_two.py (learnt) became ambiguous with
happy_number (which (a) makes run, still wrongly: int() of a character), and primality-by-trial-division-1/2 became
next_prime_number ((b) also took `if n <= 3: return True`, a part of is_prime). Dropped. Earlier tries, also dropped:
a hand rule for the filtered-sum form (not the logic the user asked for); `assert` as a precondition with a
collection rule (fibonacci-sequence-1 became climbing_stairs).

**19.10 GHC's parser checks the Haskell structure facts (haskell_ast_check.py).** User: use Haskell's own AST, better
than tree-sitter, for validation. `ghc -fno-code -ddump-parsed-ast` (parsed only; the module prepared as for the Core
path, haskell_core_pnf.prepared_source) gives every function binding of the file. A function tree-sitter reports that
GHC does not bind is a misreading and its facts are dropped; a file GHC cannot parse keeps its facts (knapsack-0-1-2.hs,
answered right, has an indentation error tree-sitter recovers from). Over the 144 held-out Haskell files GHC confirms
every function except sieve-of-eratosthenes-15.hs's `<=` and `otherwise` (a guard read as definitions); a parameter
count above GHC's is the lowerer's lambda lifting. All data: 0 differences, no answer changed.

**Later stage: the 242 held-out files that cannot be evaluated.** They are left out of this round's numbers (no
answer, and no root function runs on every battery input). This is not "no algorithm": some are fragments
(`binary-search-5.py` only calls bisect), most define functions the evaluator cannot run yet: the battery cannot call
the shape (comb-sort.c: `void f(double a[], int n)` sorting in place), a library (fibonacci-sequence-5.c: GMP), a
language version (roman-numerals-encode-5.py: Python 2 `print`), a construct the lowering lacks (factorial-9.hs: a
postfix operator `(!)`). They are taken up when the code is upgraded, each as a lowering or battery change under the
same method.

**Remaining wrong answers (7)** after 19.1-19.4: factorial-2.c -> problem_020 (exact-trace tier: problem_020's
branch sits at its helper's node); least-common-multiple-2.py -> gcd and levenshtein-distance-5.py -> problem_007 (a
curried root returns a lambda and never runs; problem_007's is_prime lowered wrongly); perfect-numbers-1.hs ->
primelib (its is_perfect_number lives in a library file); roman-numerals-encode-2.py -> magicdiamondpattern (an AP13
logic pattern too general); insertion-sort-3.py -> average_mode (`seq[:] = ...` not read as a write);
quicksort-1.py -> Cycle-sort (the partition rule above).

Next, each tested the same way: the partition rule's pivot test (quicksort-1.py); a returned lambda applied to
the next argument (lcm, Levenshtein); problem_007's is_prime.

