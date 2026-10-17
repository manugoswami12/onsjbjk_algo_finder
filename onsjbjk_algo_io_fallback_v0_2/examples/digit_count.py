def width(n):
    count = 0
    n = abs(n)
    while True:
        n = n // 10
        count += 1
        if n == 0:
            break
    return count
