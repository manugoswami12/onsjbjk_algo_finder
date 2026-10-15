"""Negative relation: digest uses a different array from the sort."""


def inspect_items(items, other_items):
    digest = 0
    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            digest = (digest * 31 + other_items[j]) % 1000000007
            if items[j] > items[j + 1]:
                items[j], items[j + 1] = items[j + 1], items[j]
    return digest
