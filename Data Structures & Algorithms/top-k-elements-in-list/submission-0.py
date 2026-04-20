class Solution:
    def topKFrequent(self, nums: List[int], k: int) -> List[int]:
        hashmap = {}
        res = []
        for num in nums:
            
            if num in hashmap:
                hashmap[num] += 1
            
            if num not in hashmap:
                hashmap[num] = 1
            
            arr = list(hashmap.items())   # [(1,1), (2,2), (3,3)]

        arr.sort(key=lambda x: x[1], reverse=True)
        res = []
        for i in range(k):
            res.append(arr[i][0])
        return res
            
        