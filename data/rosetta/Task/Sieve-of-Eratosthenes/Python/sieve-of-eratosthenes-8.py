import time

def primes2357(limit, countonly = False):
    if countonly:
        if limit < 2: yield 0; return
        if limit < 11: yield (max(4, (limit + 1) // 2)); return
    else:
        if limit < 2: return
        yield 2;
        if limit >= 3 : yield 3
        if limit >= 5: yield 5
        if limit >= 7: yield 7
        if limit < 11: return
    # wheel size is 210 = 2 * 3 * 5 * 7 or 105 for only the odd values
    # table of one wheel size of values starting at the next value of 11 for
    # values culled of multiples of 2, 3, 5, and 7; this forms a look up table of
    # indexted relative modulo prime values...
    modPrms = [ 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71
              , 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 121, 127, 131, 137, 139, 143
              , 149, 151, 157, 163, 167, 169, 173, 179, 181, 187, 191, 193, 197, 199, 209, 211 ]
    # table of gaps between the above values over one wheel (210)...
    gaps = [ 2, 4, 2, 4, 6, 2, 6, 4, 2, 4, 6, 6, 2, 6, 4, 2
           , 6, 4, 6, 8, 4, 2, 4, 2, 4, 8, 6, 4, 6, 2, 4, 6
           , 2, 6, 6, 4, 2, 4, 6, 2, 6, 4, 2, 4, 2, 10, 2, 10
           , 2, 4, 2, 4, 6, 2, 6, 4, 2, 4, 6, 6, 2, 6, 4, 2
           , 6, 4, 6, 8, 4, 2, 4, 2, 4, 8, 6, 4, 6, 2, 4, 6
           , 2, 6, 6, 4, 2, 4, 6, 2, 6, 4, 2, 4, 2, 10, 2, 10 ] # 2 loops to avoid overflow
    # table of indices of the next lowest modulo relative primes (modPrms), which
    # forms a reverse look up table from the 210 wheel indices to the `modPrm`
    # indices of the next lowest modulo relative prime value...
    ndxs = [ 0, 0, 1, 1, 1, 1, 2, 2, 3, 3, 3, 3, 4, 4, 4
           , 4, 4, 4, 5, 5, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7
           , 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 11, 11, 11
           , 11, 11, 11, 12, 12, 13, 13, 13, 13, 13, 13, 14, 14, 14, 14
           , 15, 15, 16, 16, 16, 16, 16, 16, 17, 17, 17, 17, 18, 18, 18
           , 18, 18, 18, 19, 19, 19, 19, 19, 19, 19, 19, 20, 20, 20, 20
           , 21, 21, 22, 22, 22, 22, 23, 23, 24, 24, 24, 24, 25, 25, 25
           , 25, 25, 25, 25, 25, 26, 26, 26, 26, 26, 26, 27, 27, 27, 27
           , 28, 28, 28, 28, 28, 28, 29, 29, 30, 30, 30, 30, 31, 31, 31
           , 31, 31, 31, 32, 32, 33, 33, 33, 33, 33, 33, 34, 34, 34, 34
           , 34, 34, 35, 35, 35, 35, 36, 36, 37, 37, 37, 37, 38, 38, 38
           , 38, 38, 38, 39, 39, 40, 40, 40, 40, 40, 40, 41, 41, 41, 41
           , 42, 42, 43, 43, 43, 43, 44, 44, 45, 45, 45, 45, 45, 45, 45
           , 45, 45, 45, 46, 46, 47, 47, 47, 47, 47, 47, 47, 47, 47, 47 ]
    lmtbf = (limit + 199) // 210 * 48 - 1 # integral number of wheels rounded up
    lmtsqrt = (int(limit ** 0.5) - 11)
    lmtsqrt = lmtsqrt // 210 * 48 + ndxs[lmtsqrt % 210] # round down on the wheel
    buf = bytearray(lmtbf + 1) # initialized to zeros
    for i in range(lmtsqrt + 1):
        if not buf[i]: # this makes the algorithm SoE and not Sieve of Sundaram...
            ci = i % 48; p = 210 * (i // 48) + modPrms[ci]
            s = p * p - 11; p8 = p * 48
            for _ in range(48):
                c = s // 210 * 48 + ndxs[s % 210]
                buf[c::p8] = [1] * ((lmtbf - c) // p8 + 1)
                s += p * gaps[ci]; ci += 1
    # clear primes above limit...
    lmtndx = limit - 11
    lmtndx = lmtndx // 210 * 48 + ndxs[lmtndx % 210]
    for i in range(lmtndx + 1, lmtbf + 1): buf[i] = 1
    if countonly:
        # return the count of primes...
        yield buf.count(0) + 4 # including the base primes of 2, 3, 5, and 7
    else:
        # following is slower because of generating individual primes...
        for i in range(0, lmtbf + 1, 48):
            for j in range(48):
                if not buf[i + j]: yield (210 * i + modPrms[j])

# USAGE
print("Primes to 100: ", list(primes2357(100)))
print("Number of primes to a million: ", (list(primes2357(1000000, True)))[0])
strt = time.time()
''' # slow counting of primes by iteration takes about six times longer...
gen = primes2357((n := 100000000))
primes = sum([1 for _ in gen])
'''
primes=list(primes2357((n:=100000000), True))[0]
stop = time.time()
print("Up to", n, "found", primes, "primes.")
print("This last took", stop - strt, "seconds.")
