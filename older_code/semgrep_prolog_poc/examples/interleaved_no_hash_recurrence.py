"""Negative: accumulator references a different variable in the recurrence."""


def inspect_items(items):
    digest = 0
    other = 0
    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            digest = (other * 31 + items[j]) % 1000000007
            if items[j] > items[j + 1]:
                items[j], items[j + 1] = items[j + 1], items[j]
    return digest
