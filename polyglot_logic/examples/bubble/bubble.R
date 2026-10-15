bubble_sort <- function(x) {
  n <- length(x)
  for (i in 1:(n - 1)) {
    for (j in 1:(n - i)) {
      if (x[j] > x[j + 1]) {
        t <- x[j]
        x[j] <- x[j + 1]
        x[j + 1] <- t
      }
    }
  }
  x
}
