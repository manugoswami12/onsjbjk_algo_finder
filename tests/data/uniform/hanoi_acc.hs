hanoi :: Int -> a -> a -> a -> [(a, a)]
hanoi n a b c = go n a b c []
  where
    go 0 _ _ _ acc = acc
    go k x y z acc = go (k - 1) x z y ((x, y) : go (k - 1) z y x acc)
