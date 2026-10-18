import Control.Monad (foldM)
queens n = foldM step [] [1 .. n]
  where
    step qs _ = [q : qs | q <- [1 .. n], safe q qs]
    safe q qs = and [q /= c && abs (q - c) /= d | (c, d) <- qs `zip` [1 ..]]
