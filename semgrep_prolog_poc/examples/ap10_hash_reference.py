"""Rolling-update-only reference. Does not contain any sorting operation."""

def hash_reference(items):
    digest = 0
    for i in range(len(items)):
        for j in range(len(items) - i - 1):
            digest = (digest * 31 + items[j]) % 1000000007
    return digest
