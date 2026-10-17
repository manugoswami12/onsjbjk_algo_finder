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
