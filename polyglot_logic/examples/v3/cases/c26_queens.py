def solve(n, row, cols, out):
    if row == n:
        out.append(list(cols))
        return
    for c in range(n):
        if all(c != q and abs(c - q) != row - r for r, q in enumerate(cols)):
            cols.append(c)
            solve(n, row + 1, cols, out)
            cols.pop()
