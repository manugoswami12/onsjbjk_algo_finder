from functools import reduce
from operator import mul


def factorial(n):
    return reduce(mul, range(1, n + 1), 1)


def product_of(values):
    return reduce(mul, values, 1)
