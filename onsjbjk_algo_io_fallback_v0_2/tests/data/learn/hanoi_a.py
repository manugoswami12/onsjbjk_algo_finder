def hanoi(n, src, dst, via):
    if n > 0:
        hanoi(n - 1, src, via, dst)
        print(src, dst)
        hanoi(n - 1, via, dst, src)
