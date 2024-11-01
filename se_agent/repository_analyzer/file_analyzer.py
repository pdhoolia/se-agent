import os
from se_agent.llm.api import call_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.util.markdown import extract_code_block_content

def prompt_generate_semantic_description(code):
    """ Prompt for generating semantic description of a Python file. """

    prompt = f"""
Understand the following python file and generate a semantic description for it in markdown format.

```python
{code}
```

Generated document should follow this structure:
```
# Semantic Summary
A brief semantic summary of the entire file. This should not exceed 100 token.

# Code Structures
List of classes, functions, other structures in the file with a brief semantic summary for each. Individual summaries should not exceed 50 tokens. E.g.,
- Class `ClassName`: Description of the class.
- Function `function_name`: Description of the function.
- Enum `EnumName`: Description of the enum.
- ...
```

"""
    return prompt

def generate_semantic_description(filepath):
    """
    Generate a semantic description for a code file using LLM.
    Args:
        filepath (str): The path to the code file.
    Returns:
        str: The generated semantic description.
    """
    # Check if the file is empty
    if os.path.getsize(filepath) == 0:
        return None

    with open(filepath, 'r') as file:
        code = file.read()

    prompt = prompt_generate_semantic_description(code)
    return extract_code_block_content(
        call_llm_for_task(
            task_name=TaskName.GENERATE_CODE_SUMMARY,
            messages=[
                {"role": "system", "content": "You are an expert on generating semantic descriptions for python code."},
                {"role": "user", "content": prompt}
            ]
        ).content
    )
