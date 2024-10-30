import os

from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser

from se_agent.llm.api import call_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.project import Project


TOP_N_PACKAGES = int(os.getenv('TOP_N_PACKAGES', 3))


class RelevantPackages(BaseModel):
    relevant_packages: list[str]

RELEVANT_PACKAGES_FORMAT_INSTRUCTIONS = PydanticOutputParser(pydantic_object=RelevantPackages).get_format_instructions()


class FileLocalizationSuggestion(BaseModel):
    package: str
    file: str
    confidence: float
    reason: str


class FileLocalizationSuggestions(BaseModel):
    file_localization_suggestions: list[FileLocalizationSuggestion]

FILE_LOCALIZATION_SUGGESTIONS_FORMAT_INSTRUCTIONS = PydanticOutputParser(pydantic_object=FileLocalizationSuggestions).get_format_instructions()


def prompt_identify_relevant_packages(issue_analysis, package_summaries):
    """ Generates the prompt messages to identify relevant main packages. """

    messages = []

    # System message along with package summaries to reference, and instructions
    system_message = {
        'role': 'system',
        'content': f"""You are an AI assistant that helps with software issue localization.

Following package summaries are available for your reference:

[PACKAGE-SUMMARIES-START]
{package_summaries}
[PACKAGE-SUMMARIES-END]

You understand the issues raised and discussed by the user.
Analyze any code snippets provided.
Based on the package summaries above, identify the packages most relevant to the discussion.
And finally, return a list of high-level packages (as a JSON array) that you think are most relevant for the issue and discussion.\n\n""" + RELEVANT_PACKAGES_FORMAT_INSTRUCTIONS
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

def prompt_localize_to_files(issue_analysis, documentation):
    """ Generates the prompt to localize issue to specific files and functions. """

    messages = []

    # System message along with relevant package details to reference, and instructions
    system_message = {
        'role': 'system',
        'content': f"""You are an AI assistant that specializes in analysing issues, related discussion, and understanding code. You recommend files relevant to the issue and discussion.

Following relevant package details are available for your reference:

[PACKAGE-DETAILS-START]
{documentation}
[PACKAGE-DETAILS-END]

You understand the issues raised and discussed by the user.
Analyze any code snippets provided.
Based on the package details above, suggest a list of files that you think are most relevant to the issue and discussion.
Each localization suggestion should include:
    - "package": Fully qualified package name.
    - "file": Name of the Python file.
    - "confidence": A float between 0 and 1 with two decimal points indicating the confidence you have for this suggestion to be relevant to the issue.
    - "reason": Explanation of why you think it is relevant (not to exceed 50 tokens).

Return the JSON array sorted in descending order of confidence.\n\n""" + FILE_LOCALIZATION_SUGGESTIONS_FORMAT_INSTRUCTIONS
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

def localize_issue(project: Project, issue_details, analysis_results):
    """
    Localizes the issue to specific code files, functions, and line numbers.
    """
    # Determine top_n_packages from project configuration or default
    top_n_packages = project.info.top_n_packages if project.info.top_n_packages is not None else TOP_N_PACKAGES

    # Get package summaries
    package_summaries = project.fetch_package_summaries()

    # Generate the prompt to identify relevant packages
    messages = prompt_identify_relevant_packages(analysis_results, package_summaries)

    # Call LLM to get relevant main packages
    try:
        llm_response_relevant_packages = call_llm_for_task(
            task_name=TaskName.LOCALIZE,
            messages=messages,
            response_format=RelevantPackages
        )
        if llm_response_relevant_packages:
            relevant_packages = llm_response_relevant_packages.relevant_packages
            # let's log the file_paths that are being added to the prompt
            project.logger.debug(f"Relevant Packages: {relevant_packages}")
        elif llm_response_relevant_packages.refusal:
            print(f"Refusal from LLM: {llm_response_relevant_packages.refusal}")
            return None
    except Exception as e:
        print(f"Error calling LLM for relevant packages: {e}")
        return None

    # Get detailed documentation for the identified packages
    package_details = project.fetch_package_details(relevant_packages[:top_n_packages])

    # Generate the prompt for localization to files
    messages = prompt_localize_to_files(analysis_results, package_details)

    # Call LLM for localization to files
    try:
        llm_response_file_localization_suggestions = call_llm_for_task(
            task_name=TaskName.LOCALIZE,
            messages=messages,
            response_format=FileLocalizationSuggestions
        )
        # if file_localization_response.parsed:
        if llm_response_file_localization_suggestions:
            localization_suggestions = llm_response_file_localization_suggestions.file_localization_suggestions
            project.logger.debug(f"File Localization Suggestions: {localization_suggestions}")
        elif llm_response_file_localization_suggestions.refusal:
            print(f"Refusal from LLM: {llm_response_file_localization_suggestions.refusal}")
            return None
    except Exception as e:
        print(f"Error calling LLM for localization: {e}")
        return None
    
    return localization_suggestions
