def fib(n):
    def step(prev, cur, k):
        if k == 0:
            return prev
        return step(cur, prev + cur, k - 1)
    return step(0, 1, n)


def fib_loop(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
