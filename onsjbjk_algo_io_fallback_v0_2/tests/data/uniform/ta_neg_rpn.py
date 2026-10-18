def evaluate(tokens):
    stack = []
    for t in tokens:
        if t not in "+-*":
            stack.append(int(t))
        else:
            b = stack.pop()
            a = stack.pop()
            stack.append(a + b if t == "+" else a - b if t == "-" else a * b)
    return stack.pop()
