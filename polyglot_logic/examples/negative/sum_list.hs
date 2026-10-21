module SumList where

total :: [Int] -> Int
total (x:rest) = x + total rest
total [] = 0
