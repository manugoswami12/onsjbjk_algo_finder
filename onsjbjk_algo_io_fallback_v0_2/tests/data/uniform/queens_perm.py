from itertools import permutations


def queens(n):
    found = []
    for x in permutations(range(n)):
        if len(set(x[i] + i for i in range(n))) == n and len(set(x[i] - i for i in range(n))) == n:
            found.append(x)
    return found
