def looks_like_swap(a):
    for i in range(len(a)-1):
        if a[i] > a[i+1]:
            a[i], a[i+1] = a[i], a[i]
    return a
