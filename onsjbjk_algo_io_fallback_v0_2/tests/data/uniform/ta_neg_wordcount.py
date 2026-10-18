def most_common(words):
    tally = {}
    for w in words:
        tally[w] = tally.get(w, 0) + 1
    best = None
    for w in tally:
        if best is None or tally[w] > tally[best]:
            best = w
    return best
