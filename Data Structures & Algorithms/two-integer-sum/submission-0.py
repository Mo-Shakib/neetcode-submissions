class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        hashmap = {}
        for i in range(len(nums)):
            num = nums[i]
            complement = target - num

            if complement in hashmap:
                return [hashmap[complement], i]
            
            hashmap[num] = i
