def power(base, exp):
    result = 1
    for _ in range(exp):
        result = result * base
    return result
