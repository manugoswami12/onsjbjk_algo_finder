def fibs(n):
    """Fibonacci accumulation

    An accumulation of the first n integers in the Fibonacci series. The accumulator is a
    pair of the two preceding numbers.
    """
    # Local import is more efficient.
    from itertools import accumulate

    # Note: Numbers generated in range(1, n) [or range(n-1)] call will not be used.
    return [a for a, b in accumulate(
        range(1, n),
        lambda acc, _: (acc[1],  sum(acc)),
        initial = (0, 1)
        )
    ]


# MAIN ---
if __name__ == '__main__':
    print(f'First twenty: {fibs(20)}')
