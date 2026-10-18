import qualified Data.MemoCombinators as M
lcs = memoize lcsm
  where
    lcsm [] _ = []
    lcsm _ [] = []
    lcsm (x:xs) (y:ys)
      | x == y = x : lcs xs ys
      | otherwise = longer (lcs (x:xs) ys) (lcs xs (y:ys))
longer a b = if length a > length b then a else b
memoize = M.memo2 (M.list M.char) (M.list M.char)
