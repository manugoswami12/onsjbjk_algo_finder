void marks(char *comp, int n) {
  for (int p = 2; p * p <= n; p++)
    if (!comp[p])
      for (int j = p * p; j <= n; j += p) comp[j] = 1;
}
