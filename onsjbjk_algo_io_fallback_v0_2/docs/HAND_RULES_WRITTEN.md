# Hand rules written for TheAlgorithms/Python: worked prompts (doc 04 section 17)

Each entry has four parts:
- the prompt that produced the rule, in the form of `docs/HAND_RULE_PROMPTS.md`;
- the relation written in `prolog/ta_rules.pl` (or a tightened built branch in `family_to_v02.pl` / `families_v02.pl`);
- the close negative that shaped it;
- how many clauses and fixes it took.

The fixes column records every time the first version was wrong on a real file. The relations are over the
language-neutral facts, so each one is also checked on the Rosetta C, Common Lisp and Haskell files of its task.

Run a prompt like these for a label in `benchmark/hand_rule_prompts.jsonl`; one or two relations usually do it. The
checks after writing are always the same:
- `python3 -m unittest tests.test_uniform` (own positive, close negative, clean load);
- `eval_ta.py CORPUS --run --dir <folder>` and `--status` (no new T2 claims);
- `eval_learn.py ROSETTA --stage 101` (no drop).

## Sorts (node `sequence_transformation > comparison_sort`, where learning gave one node and one behaviour to all)

| label | prompt (failure) | relation | close negative | clauses / fixes |
|---|---|---|---|---|
| bubble_sort | clash at adjacent_exchange with cocktail, gnome, odd-even, double sort | one neighbour exchange; its pass (step 1, running to its end, over the same positions) inside an outer loop or recursion | a single pass (rotate once) | 1 / 3: not double sort, not a pass that stops in order, not alternating passes |
| cocktail_shaker_sort | same clash | two passes exchanging neighbours of one sequence inside one outer loop; or one pass whose positions come from the outer loop (alternating directions) | bubble sort | 2 / 0 |
| gnome_sort | same clash | the exchange sits in one condition loop and nothing else, and no other function calls it in a loop | a pass helper called twice (Lisp cocktail) | 1 / 2 |
| odd_even_sort | same clash | the exchange's pass steps by two (`loop_step/2`, Python range step or C `for` update) | bubble sort | 1 / 0 (needed the front-end `loop_step` fact) |
| double_sort | same clash | two exchanges of one sequence in the same pass | bubble sort | 1 / 1 |
| insertion_sort | clash at shift_insertion with flash sort and intro sort; recursive insertion sort answered bubble | the pass stops when the neighbours are in order (the comparison is its own loop condition); or AP13's shift with no other loops | bubble sort's temp swap (`a[i] = a[i+1]`) | 2 / 2 |
| selection_sort | clash at select_extreme with a quicksort's partition helper | AP13's select_extreme, no self-recursion | Lomuto partition | 1 / 0 |
| shell_sort | clash at gap_exchange with comb sort | an element moved by a gap that is not 1, `q[j] = q[j - g]` | comb sort | 1 / 0 |
| comb_sort | same clash | an exchange of `i` and `i + g` (directly, through `j = i + g`, or i, j started at 0, g) while g is divided | shell sort | 3 / 2 |
| stooge_sort, slowsort | clash at stooge_recursion | three self-calls, two on the same arguments; or halves at a midpoint, then the range one shorter | each other | 1 + 1 / 0 |
| circle_sort, quick_sort | clash at partition_recursive | positions walking towards each other, split at a midpoint; quick: the partition recursion without that walk or a repeated call, or two self-calls on the sequence filtered on the two sides of one pivot | 3-way partition quicksort; stooge sort in C | 3 / 3 |
| heap_sort | (no clash: AP13's leaf) | AP13's heap leaf | - | 1 / 0 |
| merge_sort | no node or no behaviour | two self-calls on halves (indexes or slices) and a merge (AP13's, `out.append(a.pop(0))`, or a merge function) | binary search (one live call, no merge) | 1 / 2 |
| counting_sort | clash at histogram with pigeonhole sort, entropy, anagrams | the keys counted, then each key written back in key order while the count table is read at it, or each element placed at its key's prefix count | word count (a histogram, then a max) | 2 / 3 (a variable compared with `==` before it was bound) |

## Numbers

| label | prompt (failure) | relation | close negative | clauses / fixes |
|---|---|---|---|---|
| factorial | clash at range_accumulation (double factorial, Krishnamurthy, Euler 20) | the product of the counter itself over a counting loop (range, C `for`, Lisp `loop for`, Haskell `[1..n]`), step 1; or `n * f(n - 1)` | double factorial, a product over a list | 2 / 3 |
| fibonacci | clash at pair_recurrence (Lucas, Pell, Jacobsthal, climbing stairs) | `(a, b) := (b, a + b)` from a start among 0 and 1; or exactly `f(n - 1) + f(n - 2)` | Lucas (start 2, 1), Pell (`2 f(n-1) + f(n-2)`) | 2 / 1 |
| greatest_common_divisor | clash at modulo_recurrence (CRT, extended Euclid) | `{p := q, q := p mod q}` directly or through a temporary, no Bezout coefficients | extended Euclid | 1 / 2 |
| least_common_multiple | no node | `a * b / gcd(a, b)` (the file's gcd or the library one); or a multiple stepped until the other divides it | - | 2 / 0 |
| prime_check | clash at divisor_test (35 files) | `n mod d == 0` with a stepping d guards a return of false; nothing divided out, nothing summed | factorisation | 1 / 0 |
| sieve_of_eratosthenes | clash at stride_marking (Atkin, segmented) | a constant mark at `m[j]` while j steps by a stride that is an enclosing loop's variable or stepper, which reads the mark | - | 1 / 3 (a while counter; C `j += p` needed `loop_step(L, var(p))`) |
| perfect_number | io clash with other divisor sums | divisors summed, the sum compared with n | - | 1 / 0 |
| sum_of_digits | clash at digits (Armstrong, reversal) | `acc += n mod b` while `n //= b`, or the recursion | number reversal | 2 / 0 |
| collatz_sequence | clash at conditional_iteration | n halved when even, `3n + 1` when odd | - | 1 / 0 |
| luhn | no behaviour | every second digit doubled, 9 taken off, total mod 10 == 0 | - | 1 / 0 |
| binary_exponentiation | Josephus (a built branch) answered it | result times base when odd, base squared, exponent halved | naive power loop | 1 / 0 |
| count_1s_brian_kernighan_method | no behaviour | `n = n & (n - 1)` with a counter | shift-and-count | 1 / 0 |
| binary/octal/hexadecimal_to_decimal, decimal_to_binary/octal/hexadecimal | clash, no behaviour | Horner `acc = acc * b + digit of the input`; `n mod b` written as text or a table digit while `n //= b` | heap index `2i + 1` | 2 / 1 |

## Search, strings, ciphers, DP, graphs

| label | prompt (failure) | relation | close negative | clauses / fixes |
|---|---|---|---|---|
| binary_search | clash at interval_halving (tim sort, binary insertion sort) | the midpoint of lo and hi, the element there (directly or through a local) compared, lo past it or hi before it; nothing written | binary insertion sort | 1 / 2 |
| linear_search | claims on jump, ternary, interpolation | the index returned where the element equals the target, over the whole parameter sequence, the only loop | jump search | 1 / 3 (enumerate needed the tuple loop target split) |
| hamming_distance | no behaviour | a counter raised where two sequences differ at one position (same index, or one zip) | counting equal positions | 1 / 1 |
| palindrome | learned only in part | AP13's mirror compare, or the sequence compared with its reverse (`s[::-1]` needed the slice step) | - | 2 / 0 |
| atbash, xor_cipher | no behaviour | `chr(155 - code)`; `chr(ord(c) ^ key)` | - | 1 + 1 / 0 |
| max_subarray | no behaviour | Kadane: `max(x, cur + x)` and `max(best, cur)` | - | 1 / 0 |
| floyd_warshall | no behaviour | `d[i][j]` relaxed through k | - | 1 / 0 |
| dijkstra | no behaviour | a relaxation (`d[v] = d[u] + w`, a weight) of the vertex from a heap or priority queue, or from a scan for the least unvisited distance in a function it calls | Bellman-Ford | 2 / 2 |
| bellman_ford | no behaviour | the relaxation inside `range(V - 1)`, no heap, no minimum scan | DP minimisations, heapless Dijkstra | 1 / 3 |
| breadth_first_search, depth_first_search | no behaviour | a vertex taken from the front of a queue (back of a stack, or a self-call), its unvisited neighbours (the guard reads `graph[v]`) put back | RPN evaluation (a stack) | 1 + 2 / 2 |
| kahns_algorithm_topo | no behaviour | in-degrees counted and lowered, a vertex queued at zero | - | 1 / 0 |
| run_length_encoding | claims by three-sum | a count raised while neighbours are equal, emitted with the element | three-sum's duplicate skip | 1 / 1 |

## Built branches tightened (they claimed other algorithms)

| branch | claimed | tightening |
|---|---|---|
| josephus | modular exponentiation, Fermat | the modulus is the count the recursion lowers, `f(n - 1, k) mod n` |
| n_queens | Booth's rotation, Euler 49 | the keys index an occupancy table (written, or a fill of one constant); `abs(x - y)` is compared with a row distance, not a second element difference |
| run_length_encoding | three-sum, triplets | AP13's route needs the run length emitted (a count, never an index) |
| knapsack_01 | subset sum, partition, combination sum | taking adds the item's value: `max(..., T[i-1][j - w] + v)`, a guarded write, or a max with the recursion |
| towers_of_hanoi | a fractal recursion | exactly two self-calls |

## Front-end gaps found while writing rules (fixed in the v0.2 subclasses)
- **Loop steps:** AP13 keeps no loop step, so `loop_step/2` was added. It covers Python `range(a, b, k)` and C
  `for (...; i += k)`, as a constant or a variable stride.
- **Slice steps:** `s[::-1]` lost its step and lowered as `s`.
- **Tuple loop targets:** `for i, x in enumerate(q)` was one variable named `'i, x'`.
- **Chained assignments:** `a = b = e` (Python and C) lowered only `a = e`.
- **Still open:** ECL drops `(setf (aref u p) nil ...)` writes. A C comb sort's far index never appears as an assignment.
