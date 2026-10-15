"""Two interleaved logic threads: bubble sort + polynomial rolling hash updates.

The rolling digest tracks elements visited by the sorting comparisons; it is NOT
necessarily a digest of the final sorted array. No claim of cryptographic hash.
"""


def inspect_items(items):
    digest = 0
    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            digest = (digest * 31 + items[j]) % 1000000007
            if items[j] > items[j + 1]:
                items[j], items[j + 1] = items[j + 1], items[j]
    return digest
