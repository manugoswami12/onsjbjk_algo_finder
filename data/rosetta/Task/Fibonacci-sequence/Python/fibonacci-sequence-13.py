def fib():
    """Yield fib[n+1] + fib[n]"""
    yield 1
    lhs, rhs = fib(), fib()
    # move lhs one iteration ahead
    yield next(lhs)
    while True:
        yield next(lhs)+next(rhs)

f=fib()
print [next(f) for _ in range(9)]
