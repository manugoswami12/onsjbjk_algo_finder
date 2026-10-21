def fib_fast_rec(n):
    def inner_fib(prvprv, prv, c):
        if c < 1:
            return prvprv
        return inner_fib(prv, prvprv + prv, c - 1)
    return inner_fib(0, 1, n)
