def knap(w, v, cap):
    n = len(w)
    t = [[0] * (cap + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(cap + 1):
            t[i][j] = t[i - 1][j]
            if w[i - 1] <= j and t[i - 1][j - w[i - 1]] + v[i - 1] > t[i][j]:
                t[i][j] = t[i - 1][j - w[i - 1]] + v[i - 1]
    return t[n][cap]
