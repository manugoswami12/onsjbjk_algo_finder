module BinarySearch where

import Data.Array

binarySearch :: Array Int Int -> Int -> Int
binarySearch a target = go low0 high0
  where
    (low0, high0) = bounds a
    go low high
      | low > high = -1
      | a ! mid == target = mid
      | a ! mid < target = go (mid + 1) high
      | otherwise = go low (mid - 1)
      where mid = (low + high) `div` 2
