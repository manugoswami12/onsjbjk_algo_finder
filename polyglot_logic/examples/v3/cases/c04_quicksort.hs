qs [] = []
qs (p:xs) = qs [x | x <- xs, x < p] ++ [p] ++ qs [x | x <- xs, x >= p]
