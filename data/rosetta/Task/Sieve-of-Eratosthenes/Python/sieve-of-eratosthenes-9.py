# Page-Segmented Wheel-Factorized Sieve of Eratosthenes...

from bitarray import bitarray
from math import isqrt
from time import monotonic

# these primes have already been preculled...
whlprms = [ 2, 3, 5, 7, 11, 13, 17, 19 ]

# wheel size is 210 = 2 * 3 * 5 * 7 or 105 for only the odd values
# table of one wheel size of values starting at the first value of 11 for
# values culled of multiples of 2, 3, 5, and 7; this forms a look up table of
# indexed residual modulo prime values; note it still includes some non-primes as 121 = 11*2...
rsds = bytearray(
    [ 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71
    , 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 121, 127, 131, 137, 139, 143
    , 149, 151, 157, 163, 167, 169, 173, 179, 181, 187, 191, 193, 197, 199, 209, 211 ])

# table of indices of the next lowest modulo relative primes (rsds), which
# forms a reverse look up table from the 105 odds wheel indices to the `modPrm`
# indices of the next lowest modulo relative prime value...
ndxs = bytearray(
    [ 0, 1, 1, 2, 3, 3, 4, 4, 4, 5, 6, 6, 6, 7, 7
    , 8, 9, 9, 10, 10, 10, 11, 11, 11, 12, 13, 13, 13, 14, 14
    , 15, 16, 16, 16, 17, 17, 18, 18, 18, 19, 19, 19, 19, 20, 20
    , 21, 22, 22, 23, 24, 24, 25, 25, 25, 25, 26, 26, 26, 27, 27
    , 28, 28, 28, 29, 30, 30, 31, 31, 31, 32, 33, 33, 33, 34, 34
    , 34, 35, 35, 36, 37, 37, 38, 38, 38, 39, 40, 40, 40, 41, 41
    , 42, 43, 43, 44, 45, 45, 45, 45, 45, 46, 47, 47, 47, 47, 47 ])

# table of index look-ups rounded up to the next index
# used to ease start index per page calculation...
whlRndUps = bytearray(
    [ 0, 1, 3, 3, 4, 6, 6, 9, 9, 9, 10, 13, 13, 13, 15
    , 15, 16, 18, 18, 21, 21, 21, 24, 24, 24, 25, 28, 28, 28, 30
    , 30, 31, 34, 34, 34, 36, 36, 39, 39, 39, 43, 43, 43, 43, 45
    , 45, 46, 48, 48, 49, 51, 51, 55, 55, 55, 55, 58, 58, 58, 60
    , 60, 63, 63, 63, 64, 66, 66, 69, 69, 69, 70, 73, 73, 73, 76
    , 76, 76, 78, 78, 79, 81, 81, 84, 84, 84, 85, 88, 88, 88, 90
    , 90, 91, 93, 93, 94, 99, 99, 99, 99, 99, 100, 105, 105, 105, 105 ])
whlRndUps += bytearray(( ru + 105 for ru in whlRndUps )) + bytearray([210]) # two wheels for overflow!

# multi-level table index by residual bit plane, prime modulo, and
# cycle, indices to ease start index calculation per residual bit plane...
def mkstrts(): # immediately invoked anonymous function...
    buf = bytearray(48 * 48 * 48 * 2)
    mults = bytearray(48)
    for pi in range(48):
        p = rsds[pi]; s = (p * p - 11) >> 1
        for ci in range(48):
            rmlt = (rsds[(pi + ci) % 48] - rsds[pi]) >> 1
            rmlt += 105 if rmlt < 0 else 0; sn = s + p * rmlt
            snd = sn // 105; snr = sn - snd * 105
            mults[ndxs[snr]] = rmlt
        for si in range(48):
            s0 = (rsds[si] - 11) >> 1; sm0 = mults[si]
            for ci in range(48):
                smr = mults[ci]
                smr += (105 if smr < sm0 else 0) - sm0
                sn = s0 + p * smr; rofs = sn // 105
                addr = ((ci * 48 + pi) * 48 + si) << 1
                buf[addr] = smr << 1; buf[addr + 1] = rofs
    return buf
strts = mkstrts() # table too large for a literal; calculate it...

# fill from wheel pattern for each residual bit plane...
def fillBufFromFor(buf, low, fillmodsz): # fillsz is even number of 64-bit's
    modsz = len(buf) // 48; ptrnmodsz = len(whlptrn) // 48
    ptrnsz = 11 * 13 * 17 * 19 # in bits per bit plane
    lowi = (low - 11) // 210
    for ri in range(48):
        basedst = ri * modsz; basesrc = ri * ptrnmodsz
        for sri in range(0, fillmodsz, 131072):
            modndx = (lowi + sri) % ptrnsz; cpymodsz = min(131072, fillmodsz - sri)
            strt = basedst + sri; lmt = basedst + sri + cpymodsz
            pstrt = basesrc + modndx; plmt = basesrc + modndx + cpymodsz
            buf[strt:lmt] = whlptrn[pstrt:plmt]
    return

# cullsz is limit for each residual bit plane;
# bprps is a bytearray containing upper two bits of delta wheel, and
# lower six bits of the bit plane index...
def cullBufFromForBy(buf, low, cullsz, bprps):
    modsz = len(buf) // 48
    buflmt = low + cullsz * 210
    def bps(): # calculate residual plane start indices once per page
        oldbpwi = 0
        for bprp in bprps:
            oldbpwi += bprp >> 6; bpri = bprp & 0x3F
            bp = oldbpwi * 210 + rsds[bpri]; s = bp * bp
            if s >= buflmt: return
            # start index calculation for each base prime...
            if s > low: s -= low; s >>= 1
            else:
                wp = (rsds[bpri] - 11) >> 1
                s = ((low - s) >> 1) % (bp * 105)
                if s != 0:
                    s = bp * (whlRndUps[wp + (s + bp - 1) // bp] - wp) - s
            swi = s // 105; sri = ndxs[s - swi * 105]
            yield (bp, oldbpwi, bpri, swi, sri)
    bpsarr = list(bps())
    for ri in range(48): # this order improves cache associativity...
        base = ri * modsz
        for bp, bpwi, bpri, swi, sri in bpsarr:
            adji = ((ri * 48 + bpri) * 48 + sri) << 1
            adjmlt = strts[adji]; adjofst = strts[adji + 1]
            strt = base + swi + bpwi * adjmlt + adjofst; end = base + cullsz
            buf[strt:end:bp] = 1

# array of cull buffer culled of multiples of 11, 13, 17, and 19 with
# the multiples of 2, 3, 5, and 7, already eliminated due to the wheel;
# used as a wheel pattern to fill sieve buffers before further culling...
def mkwhlptrn():
    modsz = 11 * 13 * 17 * 19 + 131072
    buf = bitarray(modsz * 48)
    bprps = [ i for i in range(4)]
    cullBufFromForBy(buf, 11, modsz, bprps)
    buf[0] = 1; buf[modsz] = 1; buf[modsz * 2] = 1; buf[modsz * 3] = 1
    return buf
whlptrn = mkwhlptrn() # is 128K bits larger than the wheel size to avoid overflow...

# count the unset bits in the buffer representing numbers from `low` to `limit`...
def countBufFromFor(buf, low, limit):
    modsz = len(buf) // 48
    sizei = modsz - 1; sizej = 48
    if low + modsz * 210 - 1 > limit:
        sizei = (limit - low) // 210
        sizej = ndxs[(limit - low - sizei * 210) >> 1] + 1
    cnt = 0
    for ri in range(48):
        base = ri * modsz
        rilmt = base + sizei + (1 if ri < sizej else 0)
        cnt += buf[base:rilmt].count(0)
    return cnt

# takes a iterator of buf's and produces an iter of (i, j) values where
# i is the wheel index and j is the wheel modulo residue index...
def prmndxBufFromFor(buf, low, limit):
    modsz = len(buf) // 48
    sizei = modsz - 1; sizej = 48
    lowi = (low - 11) // 210
    if low * modsz * 210 - 1 > limit:
        sizei = (limit - low) // 210
        sizej = ndxs[(limit - low - sizei * 210) >> 1] + 1
    for i in range(sizei + 1):
        for j in range(48 if i < sizei else sizej):
            if not buf[i + j * modsz]: yield (lowi + i, j)

# produce bytearray of encoded bps, 2 bits delta whl ndx + 6 bits rsd ndx...
def bprpsToLimit(limit):
    def bprpsiter(buf, lmt): # non paged! buf wheels are a multiple of 64 bits rounded up...
        oldi = 0
        for i, j in prmndxBufFromFor(buf, 11, lmt):
            yield ((i - oldi) << 6) | j
            oldi = i
    if limit < 529: return bytearray(bprpsiter(whlptrn, limit))
    else:
        bprps = bprpsToLimit(isqrt(limit)) # recursively!
        modsz = ((limit - 11) // 210 + 127) & -64
        buf = bitarray(modsz * 48)
        fillBufFromFor(buf, 11, modsz)
        cullBufFromForBy(buf, 11, modsz, bprps)
        return bytearray(bprpsiter(buf, limit))

# produces an iterator of buffers with last one sized to fi, with the buffer
# the buffer passed into a provided function to produce iteration of result...
def bufsToLimit(limit, func):
    # 32 MegaBytes per module bit plane maximum size
    modsz = min(131072 * 8 * 64, ((limit - 11) // 210 + 127) & -64)
    bufsz = modsz * 210; buf = bitarray(modsz * 48)
    bprps = bprpsToLimit(isqrt(limit))
    for low in range(11, limit + 1, bufsz):
        fillmodsz = min(modsz, ((limit - low) // 210 + 127) & -64)
        # adjustable buffer size for efficiency
        fillBufFromFor(buf, low, fillmodsz)
        yield func(buf, low, modsz, bprps)

# produce and iterator of primes up to `limit`...
def primesTo(limit):
    if limit < 2: return
    for p in whlprms:
        if p <= limit: yield p
    if limit < 23: return
    def bufToPrimesIter(buf, low, modsz, bps):
        cullBufFromForBy(buf, low, modsz, bps)
        for i, j in prmndxBufFromFor(buf, low, limit):
            yield i * 210 + rsds[j]
    for bfrprms in bufsToLimit(limit, bufToPrimesIter):
        for prm in bfrprms: yield prm

# the result is the count of primes to the given `limit`...
def countPrimesTo(limit):
    if limit < 23:
        cnt = 0
        for p in whlprms:
            if p <= limit: cnt += 1
        return cnt
    def bufToCount(buf, low, cullmodsz, bprps):
        cullBufFromForBy(buf, low, cullmodsz, bprps)
        return countBufFromFor(buf, low, limit)
    return sum(bufsToLimit(limit, bufToCount)) + 8

# USAGE
print("Primes to 100: ", list(primesTo(100)))
print("Number of primes to a million: ", countPrimesTo(1_000_000))
strt = monotonic()
''' # slow counting of primes by iteration takes about six times longer...
gen = primesTo((n := 1_000_000_000))
primes = sum(( 1 for _ in gen ))
'''
for _ in range(n := 10): primes = countPrimesTo(limit := 1_000_000_000)
stop = monotonic()
print("Up to", limit, "repeated", n, "time(s), found", primes, "primes.")
print("This last took", stop - strt, "seconds.")
