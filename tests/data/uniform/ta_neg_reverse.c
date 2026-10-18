void mirror(int *v, int n) {
  int lo = 0, hi = n - 1, t;
  while (lo < hi) { t = v[lo]; v[lo] = v[hi]; v[hi] = t; lo++; hi--; }
}
