class Solution:
    def isPalindrome(self, s: str) -> bool:
        cleaned = ""
        
        # Step 1: clean string
        for char in s:
            if char.isalnum():
                cleaned += char.lower()
        
        # Step 2: two pointers
        left = 0
        right = len(cleaned) - 1
        
        while left < right:
            if cleaned[left] != cleaned[right]:
                return False
            
            left += 1
            right -= 1
        
        return True