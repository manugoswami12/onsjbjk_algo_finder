# Manual test: is an UNKNOWN file a new version of a known algorithm, or a new algorithm? (doc 04 section 18.2)

Kept separate from the pipeline. The decision uses the class relations (prolog/class_specs.pl) in check mode on the
file's runs on the battery (sum(2,3,X) style). The scratch tool is tools_manual/decide_new_or_known.py.

## The 5 cases checked by hand

| case | runs | class found | right? | note |
|---|---|---|---|---|
| Rosetta gnome sort (Haskell) | 11/11 | sorting | yes | new version of the sorting class |
| Rosetta quicksort-3 (Python) | 11/11 | sorting | yes | new version |
| Rosetta gcd-5, binary gcd (Python) | 8/8 | gcd | yes | new version |
| own digital_root (Python) | 47/47 | none, so "new algorithm" | **no** | TheAlgorithms has maths/digital_root.py: no relation written is not a new algorithm |
| Rosetta prime2 (Python) | 26/47 | prime_check | by luck | `any(...)` fails on odd inputs; also TheAlgorithms digital_root ran 10/47 and was given digit_sum (**wrong**) |

The test found two bugs in the class check, now fixed:
- `fib/4`, `fact/2` and `collatz/2` recursed forever when the output was already bound to another value. The check
  timed out, and the timeout was read as "no class". This turned prime2 and digital_root into false new algorithms.
- A timeout now means undecided (`ta_classes.classes` returns None).

## Sweep: the 97 held-out files at the same two nodes (sequence_transformation, numeric)

Only functions that ran on every battery input were used.

| decision | files | correct |
|---|---|---|
| new version of a known class | 10 | 10 (gcd, lcm, perfect_number, 7 sorts) |
| new algorithm (runs, no relation) | 18 | 0: every one is a known task |
| undecided | 69 | - |

Why the 18 "new algorithm" verdicts are wrong:
- **The interpreter computes the program wrongly even on full runs.** factorial-2.c returns 1, 1, 2, 3, 4, 5, from
  `result *= i` in a C for loop.
- **The algorithm takes another argument convention.** `sumDigits(num, base)` gets the battery's second integer as
  its base.
- **Only helpers produced results.** heapsort.c `downheap` and the sieve-9 buffer helpers ran; a helper's
  input->output is not the algorithm.

## Decision
- "New version of a known class" is reliable here: 16/16 so far, counting the 6 of the class fallback test. It can
  become a branch at the node the file reaches, labelled with the class (sorting, not which sort). That branch still
  needs the same test on the 1346 corpus files before anything else.
- "New algorithm" is not reliable: 0/19. A missing relation, an interpreter error, an argument convention or a helper
  all look the same as a new algorithm. No rule may be created from it. Such files stay UNKNOWN.
