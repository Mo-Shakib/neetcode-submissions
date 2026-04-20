class Solution:
    def isValid(self, s: str) -> bool:
        stack = []

        for i in s:
            if i in ['(', '{', '[']:
                stack.append(i)

            elif i in [')', '}', ']']:
                if len(stack) == 0:
                    return False

                if i == ')':
                    if stack[-1] == '(':
                        stack.pop()
                    else:
                        return False

                if i == '}':
                    if stack[-1] == '{':
                        stack.pop()
                    else:
                        return False

                if i == ']':
                    if stack[-1] == '[':
                        stack.pop()
                    else:
                        return False

        return len(stack) == 0