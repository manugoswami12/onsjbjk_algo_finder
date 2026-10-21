bubble <- function(v) {
  for (k in seq_len(length(v) - 1)) {
    for (i in seq_len(length(v) - k)) {
      if (v[i] > v[i + 1]) {
        v[c(i, i + 1)] <- v[c(i + 1, i)]
      }
    }
  }
  v
}
