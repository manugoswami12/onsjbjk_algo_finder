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
