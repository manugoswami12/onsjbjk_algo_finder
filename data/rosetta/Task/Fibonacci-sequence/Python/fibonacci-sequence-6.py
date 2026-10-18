def fib_memo():
    pad = {0:0, 1:1}
    def sub_func(n):
        if not n in pad:
            pad[n] = sub_func(n-1) + sub_func(n-2)
        return pad[n]
    return sub_func

fm = fib_memo()
for i in range(1,31):
    print(fm(i))
