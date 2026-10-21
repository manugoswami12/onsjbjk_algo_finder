import Data.List (group)
encode :: String -> [(Int, Char)]
encode = map (\g -> (length g, head g)) . group
