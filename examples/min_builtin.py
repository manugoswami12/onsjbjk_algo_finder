def smallest(nums):
    m = nums[0]
    for x in nums:
        m = min(m, x)
    return m
