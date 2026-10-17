import Data.List (group, sort)
uniq :: [Int] -> [Int]
uniq = map head . group . sort
