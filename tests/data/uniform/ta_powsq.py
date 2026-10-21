def power(base, exp):
    result = 1
    while exp > 0:
        if exp % 2 == 1:
            result = result * base
        base = base * base
        exp = exp // 2
    return result
