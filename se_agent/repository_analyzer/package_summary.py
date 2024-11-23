"""Module for generating package summaries using an LLM."""

from se_agent.llm.api import call_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.util.markdown import extract_code_block_content

def prompt_generate_package_summary(package_name: str, documentation: str) -> str:
    """Generates a prompt for summarizing a Python package.

    Args:
        package_name (str): Name of the package to summarize.
        documentation (str): Hierarchical documentation of the package.

    Returns:
        str: The prompt to be used by the LLM to generate a package summary.
    """
    prompt = f"""
Understand the following hierarchical documentation for python package {package_name}, with semantic description of sub-packages, files, classes, and functions contained.

```markdown
{documentation}
```

Now generate an abstractive package summary in markdown format with the following structure:
```
# <Package Name>

## Semantic Summary
A very crisp description of the full package semantics. This should not exceed 150 tokens.

## Contained code structure names
Just a comma separated listing of contained sub-package, file, class, function, enum, or structure names. E.g.,
`package1`, `sub_package`, `file_name.py`, `ClassName`, `function_name`, `EnumName`, `__init__.py` ...
```

Note: Whole package summary should not exceed 512 tokens. For large packages skip names of contained code structures that are relatively less importance.
"""
    return prompt

def generate_package_summary(package_name: str, package_details_content: str) -> str:
    """
    Generate a package summary for a single top-level package using its detailed documentation content.
        Args:
        package_name (str): The name of the top-level package.
        package_details_content (str): The detailed documentation content for the package.

    Returns:
        str: The generated package summary.
    """
    # Generate the prompt for the LLM
    prompt = prompt_generate_package_summary(package_name, package_details_content)
    try:
        # Call the LLM to generate the package summary
        package_summary = call_llm_for_task(
            task_name=TaskName.GENERATE_PACKAGE_SUMMARY,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at generating higher order package summaries for detailed package documentation"
                },
                {"role": "user", "content": prompt}
            ]
        ).content
    except Exception as e:
        raise RuntimeError(f"Error generating summary for package {package_name}") from e

    # Extract and return the code block content from the LLM's response
    return extract_code_block_content(package_summary)