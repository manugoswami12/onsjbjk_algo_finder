"""Python references for the AP13 v2 tests (written for AP13; corpus-style)."""


def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("factorial() not defined for negative values")
    value = 1
    for i in range(1, n + 1):
        value *= i
    return value


def factorial_recursive(n: int) -> int:
    if n < 0:
        raise ValueError("negative")
    return 1 if n in (0, 1) else n * factorial_recursive(n - 1)


def gcd(a: int, b: int) -> int:
    return abs(b) if a == 0 else gcd(b % a, a)


def poly_hash(text: str) -> int:
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) % 1000003
    return h


def add(a: int, b: int) -> int:
    return a + b
