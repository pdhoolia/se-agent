import os

from se_agent.llm.api import call_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.localizer import FileLocalizationSuggestions
from se_agent.project import Project


TOP_N_FILES = int(os.getenv('TOP_N_FILES', 3))


def prompt_generate_change_suggestions(issue_analysis, file_suggestions, code_files):
    """ Generates the prompt to localize issue to specific files and functions. """

    messages = []

    # System message along with relevant package details to reference, and instructions
    system_message = {
        'role': 'system',
        'content': f"""You are an AI assistant that specializes in analysing issues and understanding code, and make code change suggestions to address issues.

Following files have been suggested as relevant to the issue and discussion:

[FILE-SUGGESTIONS-START]
{file_suggestions}
[FILE-SUGGESTIONS-END]

Here are the corresponding code files:
{code_files}

Based on the issue details and ensuing discussion please suggest code or changes to it in these files and (or any new code) along with your reasoning. In case of code change, don't write the entire code or function. Focus on just the relevant parts that are changed."""
    }
    messages.append(system_message)

    # The conversation from issue_analysis['conversation']. It includes the issue details and the ensuing conversation.
    conversation = issue_analysis.get('conversation', [])
    for message in conversation:
        # Map roles appropriately
        if message['role'] == 'user':
            role = 'user'
        else:
            role = 'assistant'
        messages.append({'role': role, 'content': message['content']})

    return messages

def suggest_changes(project: Project, analysis_results: dict, localization_suggestions: FileLocalizationSuggestions) -> str :
    """ Suggest code changes """
    # Determine top_n_files from project configuration or default
    top_n_files = project.info.top_n_files if project.info.top_n_files is not None else TOP_N_FILES

    # Get the files being suggested
    files = project.fetch_code_files([
        (suggestion.package.replace('.', os.sep), suggestion.file)
        for suggestion in localization_suggestions[:top_n_files]
    ])

    # let's log the file_paths that are being added to the prompt
    project.logger.debug(f"Files being added to the prompt: {[file[0] for file in files]}")

    # let's build the code_files part of the prompt input from files
    code_files = ""
    for file_path, file_content in files:
        code_files += f"""
file: {file_path}
```
{file_content}
```

"""

    # Generate the prompt for change suggestions
    messages = prompt_generate_change_suggestions(analysis_results, str(localization_suggestions), code_files)

    # Call LLM for change suggestions
    try:
        change_suggestions_response = call_llm_for_task(
            task_name=TaskName.GENERATE_SUGGESTIONS,
            messages=messages
        ).content
    except Exception as e:
        print(f"Error calling LLM for change suggestions: {e}")
        return None
    
    return change_suggestions_response
