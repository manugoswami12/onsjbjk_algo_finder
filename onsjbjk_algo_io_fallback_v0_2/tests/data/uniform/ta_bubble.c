void sort_passes(int *v, int n) {
  for (int p = 0; p < n - 1; p++)
    for (int k = 0; k < n - 1 - p; k++)
      if (v[k] > v[k + 1]) { int t = v[k]; v[k] = v[k + 1]; v[k + 1] = t; }
}
