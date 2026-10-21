def table(num):
    marks = [True] * (num + 1)
    p = 2
    while p * p <= num:
        if marks[p]:
            for i in range(p * p, num + 1, p):
                marks[i] = False
        p += 1
    return [q for q in range(2, num + 1) if marks[q]]
