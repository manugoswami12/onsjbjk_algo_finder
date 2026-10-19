# Proposed class branches (doc 04 section 18.3): held-out Rosetta files

The pipeline answer is kept; a proposed branch (prolog/proposed_branches.pl, learned from TheAlgorithms files) answers only a file the pipeline left UNKNOWN. Separate from the pipeline (eval_proposed.py).

| language | files | pipeline answers | branch answers (new) | correct / wrong | precision | recall | branch fired (all files) | branch right / wrong |
|---|---|---|---|---|---|---|---|---|
| C | 69 | 32 | 0 | 31 / 1 | 96.9% | 44.9% | 2 | 2 / 0 |
| Common-Lisp | 75 | 43 | 0 | 42 / 1 | 97.7% | 56.0% | 0 | 0 / 0 |
| Haskell | 144 | 30 | 1 | 30 / 1 | 96.8% | 20.8% | 3 | 3 / 0 |
| Python | 162 | 62 | 1 | 58 / 5 | 92.1% | 35.8% | 9 | 9 / 0 |
| all | 450 | 167 | 2 | 161 / 8 | 95.3% | 35.8% | 14 | 14 / 0 |

## Held-out files answered by a branch (2)

- Task/Sorting-algorithms-Bubble-sort/Haskell/sorting-algorithms-bubble-sort-1.hs: sorting (right), task Sorting-algorithms-Bubble-sort
- Task/Sorting-algorithms-Insertion-sort/Python/sorting-algorithms-insertion-sort-2.py: sorting (right), task Sorting-algorithms-Insertion-sort

## Branch wrong on any held-out file, answered or not (0)


## TheAlgorithms files a branch learned from other files applies to (25)

- divide_and_conquer/mergesort.py: sorting (pipeline answer mergesort)
- sorts/adaptive_merge_sort.py: sorting (pipeline answer Sorting-algorithms-Merge-sort)
- sorts/bubble_sort.py: sorting (pipeline answer Sorting-algorithms-Bubble-sort)
- sorts/bubble_sort_recursive.py: sorting (pipeline answer Sorting-algorithms-Bubble-sort)
- sorts/circle_sort.py: sorting (pipeline answer circle_sort)
- sorts/cocktail_shaker_sort.py: sorting (pipeline answer Sorting-algorithms-Cocktail-sort)
- sorts/comb_sort.py: sorting (pipeline answer Sorting-algorithms-Comb-sort)
- sorts/double_sort.py: sorting (pipeline answer double_sort)
- sorts/exchange_sort.py: sorting (pipeline answer exchange_sort)
- sorts/gnome_sort.py: sorting (pipeline answer Sorting-algorithms-Gnome-sort)
- sorts/heap_sort.py: sorting (pipeline answer Sorting-algorithms-Heapsort)
- sorts/insertion_sort.py: sorting (pipeline answer Sorting-algorithms-Insertion-sort)
- sorts/merge_insertion_sort.py: sorting (pipeline answer merge_insertion_sort)
- sorts/odd_even_sort.py: sorting (pipeline answer odd_even_sort)
- sorts/odd_even_transposition_single_threaded.py: sorting (pipeline answer odd_even_transposition_single_threaded)
- sorts/pigeon_sort.py: sorting (pipeline answer pigeon_sort)
- sorts/quick_sort.py: sorting (pipeline answer Sorting-algorithms-Quicksort)
- sorts/recursive_insertion_sort.py: sorting (pipeline answer Sorting-algorithms-Insertion-sort)
- sorts/recursive_quick_sort.py: sorting (pipeline answer Sorting-algorithms-Quicksort)
- sorts/reverse_selection.py: sorting (pipeline answer reverse_selection)
- sorts/selection_sort.py: sorting (pipeline answer Sorting-algorithms-Selection-sort)
- sorts/shell_sort.py: sorting (pipeline answer Sorting-algorithms-Shell-sort)
- sorts/shrink_shell_sort.py: sorting (pipeline answer Sorting-algorithms-Shell-sort)
- sorts/stooge_sort.py: sorting (pipeline answer Sorting-algorithms-Stooge-sort)
- sorts/tim_sort.py: sorting (pipeline answer tim_sort)
