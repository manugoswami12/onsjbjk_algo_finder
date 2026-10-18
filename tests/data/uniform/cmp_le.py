def best(w, v, n, cap):
    total = 0
    for i in range(n):
        if w[i] <= cap:
            total = total + v[i]
    return total
