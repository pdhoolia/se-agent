import re

def extract_code_block_content(input_string: str) -> str:
    """Extracts the content inside a code block fence from the input string.

    Args:
        input_string (str): The string that may contain a code block fenced with triple backticks.

    Returns:
        str: The content inside the code block fence if found; otherwise, returns the original input string.
    """
    # Compile regex pattern to match exactly one opening and one closing code fence
    pattern = re.compile(r'^```(?:\w+)?\r?\n(.*?)\r?\n```$', re.DOTALL)

    # Check if the input_string is entirely wrapped in a code block fence
    match = pattern.match(input_string)
    if match:
        # If matched, extract the content inside the fences
        input_string = match.group(1)

    return input_string