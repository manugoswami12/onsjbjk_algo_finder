def say(n):
    out = []
    for k in range(1, n + 1):
        if k % 15 == 0:
            out.append("FizzBuzz")
        elif k % 3 == 0:
            out.append("Fizz")
        elif k % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(k))
    return out
