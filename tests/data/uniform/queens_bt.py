def place(n, row, cols, d1, d2, found):
    if row == n:
        found.append(list(cols))
        return
    for c in range(n):
        if c not in cols and row + c not in d1 and row - c not in d2:
            place(n, row + 1, cols + [c], d1 + [row + c], d2 + [row - c], found)
