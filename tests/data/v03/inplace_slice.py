def insert_sorted(seq):
    for i in range(1, len(seq)):
        key = seq[i]
        j = 0
        while j < i and seq[j] <= key:
            j += 1
        seq[:] = seq[:j] + [key] + seq[j:i] + seq[i + 1:]
