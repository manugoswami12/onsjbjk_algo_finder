void shaker(int *v, int n) {
  int lo = 0, hi = n - 1, moved = 1, k, t;
  while (moved) {
    moved = 0;
    for (k = lo; k < hi; k++)
      if (v[k] > v[k + 1]) { t = v[k]; v[k] = v[k + 1]; v[k + 1] = t; moved = 1; }
    hi--;
    for (k = hi; k > lo; k--)
      if (v[k - 1] > v[k]) { t = v[k]; v[k] = v[k - 1]; v[k - 1] = t; moved = 1; }
    lo++;
  }
}
