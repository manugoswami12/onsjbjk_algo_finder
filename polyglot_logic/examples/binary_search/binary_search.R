binary_search <- function(x, target) {
  low <- 1
  high <- length(x)
  while (low <= high) {
    mid <- (low + high) %/% 2
    if (x[mid] == target) {
      return(mid)
    } else if (x[mid] < target) {
      low <- mid + 1
    } else {
      high <- mid - 1
    }
  }
  -1
}
