void pick(int *v, int n) {
  for (int i = 0; i < n - 1; i++) {
    int m = i;
    for (int j = i + 1; j < n; j++)
      if (v[j] < v[m]) m = j;
    int t = v[i]; v[i] = v[m]; v[m] = t;
  }
}
