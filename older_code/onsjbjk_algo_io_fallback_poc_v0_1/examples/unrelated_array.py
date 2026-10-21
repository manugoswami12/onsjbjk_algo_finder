def not_comparison_sort(a, b):
    for i in range(len(a)-1):
        if a[i] > a[i+1]:
            b[i], b[i+1] = b[i+1], b[i]
    return b
