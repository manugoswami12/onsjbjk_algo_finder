import Data.List (nub, permutations)
distinct f = length . nub . zipWith f [0..]
queens n = filter (\x -> distinct (+) x == n && distinct (-) x == n) $ permutations [0..n-1]
