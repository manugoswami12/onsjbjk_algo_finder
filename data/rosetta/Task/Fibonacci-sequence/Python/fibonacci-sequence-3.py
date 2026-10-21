def fib4k(n): # FIBonacci's numbers, Binet's Formula, Barron's Binomial expansion, Kra's code.
    # (c) 2025 David A. Kra GNUFDL1.3 and Copyleft Creative Commons CC BY-SA Attribution-ShareAlike
    #
    # ALL INTEGER. Tested up to Fib(4000).
    # NOTE: This implementation is NOT faster than simply progressing up to Fib(n) by addition, starting from Fib(1).
    # Thanks, Acknowledgement, and Appreciation to Barron https://stackexchange.com/users/9594318/barron
    # No floats were exploited in the production of this function.
    # References:
    #   https://math.stackexchange.com/questions/674570/prove-that-binets-formula-gives-an-integer-using-the-binomial-theorem
    #   https://math.stackexchange.com/questions/2002702/fibonacci-identity-with-binomial-coefficients
    #   https://artofproblemsolving.com/wiki/index.php/Binet%27s_Formula
    #       https://latex.artofproblemsolving.com/8/6/d/86d486c560727727342090b432e23ba85ac098b1.png
    #   https://www.geeksforgeeks.org/find-nth-fibonacci-number-using-binets-formula/
    #   https://discuss.geeksforgeeks.org/comment/540dc728-8cfc-41e3-853e-e920e0a85101/gfg
    #    # Fn=(1/(2**(n-1))) * SUM(j=0,n//2,((5**j)*comb(n,2*j+1))
    #
    #   qc == Quick Combination. Instead of using comb, with its loop on each call,
    #           derive the next (  comb(n,2*j+1)  ) by building up from what had already been calculated,
    #           Given comb(n,2*j+1), then
    #                 comb(n,2*(j+1)+1) = comb(n,2*j+1) *  (n-(2*j+1))*(n-2*j+1)-1) // ( (2*j+1)+1)*(2*j+1)+2) )
    #   qp == Quick Power. Instead of using 5**j, derive the next fttj as fttj*=5
    #
    f=0
    fttj=1
    qc=n # = comb(n,1)
    for j in range(0,int(n/2+1)):
        f+=fttj*qc  # (5**k)*qc #  qc == comb(n,2*k+1)
        j2p1=j*2+1
        # calculate the 5**k and the combinations for the next iteration,
        #   but for now, k and k2p1 have this iteration's values.
        fttj*=5
        qc=qc* (n-j2p1)*(n-j2p1-1) // ( (j2p1+1)*(j2p1+2) )   # for the next iteration

    f=f//(2 ** (n-1) )
    return f


</syntaxhighlight lang="python">
<pre>
Test


print([[i,fib4k(i)] for i in [4,40,400,4000]])


output

[[4, 3], [40, 102334155], [400, 176023680645013966468226945392411250770384383304492191886725992896575345044216019675], [4000, 39909473435004422792081248094960912600792570982820257852628876326523051818641373433549136769424132442293969306537520118273879628025443235370362250955435654171592897966790864814458223141914272590897468472180370639695334449662650312874735560926298246249404168309064214351044459077749425236777660809226095151852052781352975449482565838369809183771787439660825140502824343131911711296392457138867486593923544177893735428602238212249156564631452507658603400012003685322984838488962351492632577755354452904049241294565662519417235020049873873878602731379207893212335423484873469083054556329894167262818692599815209582517277965059068235543139459375028276851221435815957374273143824422909416395375178739268544368126894240979135322176080374780998010657710775625856041594078495411724236560242597759185543824798332467919613598667003025993715274875]]

</pre>

===Iterative===
<syntaxhighlight lang="python">def fib_iter(n):
    if n < 2:
        return n
    fib_prev = 1
    fib = 1
    for _ in range(2, n):
        fib_prev, fib = fib, fib + fib_prev
    return fib
