rev <- function(v) {
  n <- length(v)
  for (i in seq_len(n %/% 2)) {
    v[c(i, n - i + 1)] <- v[c(n - i + 1, i)]
  }
  v
}
