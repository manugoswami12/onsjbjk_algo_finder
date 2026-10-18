def find(text, pat, b=256, m=1000003):
    k = len(pat)
    hp = ht = 0
    power = 1
    for i in range(k):
        hp = (ord(pat[i]) + hp * b) % m
        ht = (ord(text[i]) + ht * b) % m
        if i < k - 1:
            power = (power * b) % m
    for i in range(len(text) - k + 1):
        if hp == ht and text[i:i + k] == pat:
            return i
        if i < len(text) - k:
            ht = ((ht - ord(text[i]) * power) * b + ord(text[i + k])) % m
    return -1
