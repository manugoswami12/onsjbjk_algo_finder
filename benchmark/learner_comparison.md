# Learner comparison on the fresh 55 (same training: 76 labelled files; same frozen key)

| Contender | Precision | Recall | Wrong on negatives |
|---|---|---|---|
| A. v0.2 witnesses only | 9/11 = 81.8% | 9/25 = 36.0% | 0/30 |
| B. A + new learner learn_v2 (AST winnowing) | 9/11 = 81.8% | 9/25 = 36.0% | 0/30 |
| C. A + original AP13 learn-dir (exact traced logic) | 9/11 = 81.8% | 9/25 = 36.0% | 0/30 |
| D. A + original AP13 io_catalog (behaviour / I/O) | 14/16 = 87.5% | 14/25 = 56.0% | 1/30 (pigeon_sort) |

Chosen: D (original io_catalog). The pre-stated tie rule demanded 0 wrong negatives, which D misses by one;
D was chosen anyway because it is better on both precision and recall, the user's criterion. Stated openly.
