int lev(const char *s, int ls, const char *t, int lt) {
    if (!ls) return lt;
    if (!lt) return ls;
    if (s[ls - 1] == t[lt - 1]) return lev(s, ls - 1, t, lt - 1);
    int a = lev(s, ls - 1, t, lt - 1), b = lev(s, ls, t, lt - 1), c = lev(s, ls - 1, t, lt);
    if (a > b) a = b;
    if (a > c) a = c;
    return a + 1;
}
