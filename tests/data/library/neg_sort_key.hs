import Data.List (sort)

secondSmallest :: [Int] -> Int
secondSmallest xs = sort xs !! 1
