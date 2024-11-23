"""Module for generating semantic descriptions of Python files using LLM."""

import os
from se_agent.llm.api import call_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.util.markdown import extract_code_block_content

def prompt_generate_semantic_description(code):
    """Generates a prompt for the LLM to create a semantic description of a Python file.

    Args:
        code (str): The content of the Python file.

    Returns:
        str: A formatted prompt to provide to the LLM.
    """
    prompt = f"""
Understand the following Python file and generate a semantic description for it in markdown format.

```python
{code}
```

Generated document should follow this structure:
```
# Semantic Summary
A brief semantic summary of the entire file. This should not exceed 100 tokens.

# Code Structures
List of classes, functions, and other structures in the file with a brief semantic summary for each. Individual summaries should not exceed 50 tokens. E.g.,
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
        filepath (str): Path to the file.

    Returns:
        str or None: The generated semantic description in markdown format, or None if the file is empty.
    """
    # Check if the file is empty
    if os.path.getsize(filepath) == 0:
        return None

    with open(filepath, 'r') as file:
        code = file.read()

    # Generate the prompt for the LLM
    prompt = prompt_generate_semantic_description(code)

    # Call the LLM to generate the semantic description
    return extract_code_block_content(
        call_llm_for_task(
            task_name=TaskName.GENERATE_CODE_SUMMARY,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert on generating semantic descriptions for code."
                },
                {"role": "user", "content": prompt}
            ]
        ).content
    )