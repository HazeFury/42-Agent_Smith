SYSTEM_PROMPT = '''You solve Python programming tasks step by step.

Each turn, write a short Thought, then exactly one Python code block, then stop:

Thought: <your reasoning>
```python
<your code>
```<end_code>

You will then receive the result of your code as an Observation.
Use print() to see values.

When your solution is ready, submit the complete function code as a string:

```python
final_answer("""def add(a, b):
    return a + b""")
```<end_code>'''


class PromptManager:
    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT
    
