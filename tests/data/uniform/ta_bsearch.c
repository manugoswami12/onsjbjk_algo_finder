int find(int *v, int n, int x) {
  int lo = 0, hi = n - 1;
  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    if (v[mid] == x) return mid;
    if (v[mid] < x) lo = mid + 1; else hi = mid - 1;
  }
  return -1;
}
