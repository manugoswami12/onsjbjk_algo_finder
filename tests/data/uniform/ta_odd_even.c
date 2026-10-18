void brick(int *v, int n) {
  int sorted = 0, k, t;
  while (!sorted) {
    sorted = 1;
    for (k = 1; k < n - 1; k += 2)
      if (v[k] > v[k + 1]) { t = v[k]; v[k] = v[k + 1]; v[k + 1] = t; sorted = 0; }
    for (k = 0; k < n - 1; k += 2)
      if (v[k] > v[k + 1]) { t = v[k]; v[k] = v[k + 1]; v[k + 1] = t; sorted = 0; }
  }
}
