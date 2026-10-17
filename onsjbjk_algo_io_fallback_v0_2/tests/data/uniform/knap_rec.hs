best [] _ = 0
best ((w, v) : rest) cap
  | w <= cap = max (best rest cap) (v + best rest (cap - w))
  | otherwise = best rest cap
