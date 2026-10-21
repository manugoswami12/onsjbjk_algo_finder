module Bubble where

pass :: [Int] -> [Int]
pass (x:y:rest)
  | x > y     = y : pass (x:rest)
  | otherwise = x : pass (y:rest)
pass xs = xs

bubbleSort :: [Int] -> [Int]
bubbleSort xs = go (length xs) xs
  where
    go 0 ys = ys
    go k ys = go (k - 1) (pass ys)
