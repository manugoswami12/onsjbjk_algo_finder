void thirds(int *v, int lo, int hi) {
  if (v[lo] > v[hi]) { int t = v[lo]; v[lo] = v[hi]; v[hi] = t; }
  if (hi - lo + 1 > 2) {
    int third = (hi - lo + 1) / 3;
    thirds(v, lo, hi - third);
    thirds(v, lo + third, hi);
    thirds(v, lo, hi - third);
  }
}
