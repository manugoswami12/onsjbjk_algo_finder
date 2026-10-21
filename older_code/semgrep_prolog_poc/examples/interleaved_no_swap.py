"""Negative: valid hash recurrence but no bubble sort (no swap)."""


def inspect_items(items):
    digest = 0
    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            digest = (digest * 31 + items[j]) % 1000000007
            if items[j] > items[j + 1]:
                pass
    return digest
