countdown :: Int -> Int
countdown 0 = 0
countdown n = countdown (n - 1)
