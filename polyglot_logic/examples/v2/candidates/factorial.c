long factorial(int n) {
    long r = 1;
    for (int k = 2; k <= n; k++)
        r *= k;
    return r;
}
