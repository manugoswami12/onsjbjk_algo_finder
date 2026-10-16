void caesar(char *s, int n, int k) {
    for (int i = 0; i < n; i++)
        s[i] = 'a' + (s[i] - 'a' + k) % 26;
}
