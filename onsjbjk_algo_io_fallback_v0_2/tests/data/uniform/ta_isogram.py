def no_repeats(word):
    w = word.lower()
    return len(set(w)) == len(w)
