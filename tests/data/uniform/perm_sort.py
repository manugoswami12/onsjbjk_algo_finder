from itertools import permutations


def perm_sort(xs):
    for p in permutations(xs):
        if all(p[i] <= p[i + 1] for i in range(len(p) - 1)):
            return list(p)
