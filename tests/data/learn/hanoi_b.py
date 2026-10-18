def solve(k, a, b, c):
    if k == 1:
        print(a, c)
        return
    solve(k - 1, a, c, b)
    print(a, c)
    solve(k - 1, b, a, c)
