def nth_fib(n):
    """Nth Fibonacci term (by folding)

    Nth integer in the Fibonacci series.
    """
    from functools import reduce
    return reduce(
        lambda acc, _: (acc[1], sum(acc)),
        range(1, n),
        (0, 1)
    )[0]


# MAIN ---
if __name__ == '__main__':
    n = 1000
    print(f'{n}th term: {nth_fib(n)}')
