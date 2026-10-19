def fib(n):
    if n < 2:
        return n
    a = fib(n - 1)
    b = fib(n - 2)
    return a + b
