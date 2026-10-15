"""Negative relation: sorting and hash-update exist in distinct functions."""


def sort_items(items):
    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            if items[j] > items[j + 1]:
                items[j], items[j + 1] = items[j + 1], items[j]


def fingerprint(items):
    digest = 0
    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            digest = (digest * 31 + items[j]) % 1000000007
    return digest
