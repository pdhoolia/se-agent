"""Implementation of a hierarchical localization strategy for resolving issues.

This module defines the `HierarchicalLocalizationStrategy` class, which uses a hierarchical 
approach to localize issues to relevant code files based on semantic summaries. The strategy 
relies on an LLM to identify relevant packages and files by analyzing the issue details and 
semantic summaries of the project's packages and files.
"""

import logging
import os
from typing import Dict, List, Any

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from se_agent.llm.api import call_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.localize.localization_strategy import LocalizationStrategy
from se_agent.project import Project

logger = logging.getLogger("se-agent")

class RelevantPackages(BaseModel):
    """Data model for representing relevant packages identified by the LLM."""
    relevant_packages: list[str]


RELEVANT_PACKAGES_FORMAT_INSTRUCTIONS = PydanticOutputParser(
    pydantic_object=RelevantPackages
).get_format_instructions()


class FileLocalizationSuggestion(BaseModel):
    """Data model for representing a file localization suggestion."""
    package: str
    file: str
    confidence: float
    reason: str


class FileLocalizationSuggestions(BaseModel):
    """Data model for representing multiple file localization suggestions."""
    file_localization_suggestions: list[FileLocalizationSuggestion]


FILE_LOCALIZATION_SUGGESTIONS_FORMAT_INSTRUCTIONS = PydanticOutputParser(
    pydantic_object=FileLocalizationSuggestions
).get_format_instructions()


def prompt_identify_relevant_packages(issue: Dict[str, Any], package_summaries: str) -> List[Dict[str, str]]:
    """Generates the prompt messages for identifying relevant main packages.

    Args:
        issue (Dict[str, Any]): A dictionary containing issue details, including conversation.
        package_summaries (str): Semantic summaries of all packages in the project.

    Returns:
        List[Dict[str, str]]: Messages to be sent to the LLM.
    """
    messages = []

    # System message with context and instructions
    system_message = {
        'role': 'system',
        'content': f"""You are an AI assistant that helps with software issue localization.

You understand the issue content, any embedded code snippets, and any related discussion across messages.
Based on the provided package summaries, you identify the most relevant packages and return a JSON-formatted output as follows:
{RELEVANT_PACKAGES_FORMAT_INSTRUCTIONS}

Here are the package summaries:
[PACKAGE-SUMMARIES-START]
{package_summaries}
[PACKAGE-SUMMARIES-END]
"""
    }
    messages.append(system_message)

    # Include the conversation messages from the issue
    conversation = issue.get('conversation', [])
    for message in conversation:
        role = 'user' if message['role'] == 'user' else 'assistant'
        messages.append({'role': role, 'content': message['content']})

    return messages


def prompt_localize_to_files(issue: Dict[str, Any], package_details: str) -> List[Dict[str, str]]:
    """Generates the prompt messages for localizing an issue to specific files.

    Args:
        issue (Dict[str, Any]): A dictionary containing issue details, including conversation.
        package_details (str): Semantic summaries of the relevant packages and their files.

    Returns:
        List[Dict[str, str]]: Messages to be sent to the LLM.
    """
    messages = []

    # System message with context and instructions
    system_message = {
        "role": "system",
        "content": f"""You are an AI assistant specializing in localizing issues to related files based on semantic summaries of code packages and their files.

You return the files that are most relevant to the issue in the following JSON format:
{FILE_LOCALIZATION_SUGGESTIONS_FORMAT_INSTRUCTIONS}

Here are the semantic summaries of the relevant packages:
---
{package_details}
---
"""
    }
    messages.append(system_message)

    # Include the conversation messages from the issue
    conversation = issue.get('conversation', [])
    for message in conversation:
        role = 'user' if message['role'] == 'user' else 'assistant'
        messages.append({'role': role, 'content': message['content']})

    return messages


class HierarchicalLocalizationStrategy(LocalizationStrategy):
    """Implements the hierarchical localization strategy for issue resolution.

    Attributes:
        project (Project): The project instance containing metadata and configuration.
    """
    def __init__(self, project: Project):
        """Initializes the strategy with the project instance.

        Args:
            project (Project): The project instance containing metadata and configuration.
        """
        self.project = project

    def localize(self, issue: Dict[str, Any], top_n: int) -> List[str]:
        """Localizes the issue to specific files.

        Args:
            issue (Dict[str, Any]): A dictionary containing issue details and conversation.
            top_n (int): The maximum number of localization results to return.

        Returns:
            List[str]: A list of file paths relevant to the issue.
        """
        # Determine top_n packages from project configuration or default
        if self.project.info.top_n_packages:
            top_n = self.project.info.top_n_packages

        # Fetch package summaries from the project
        package_summaries = self.project.fetch_package_summaries()

        # Generate the prompt for identifying relevant packages
        messages = prompt_identify_relevant_packages(issue, package_summaries)

        try:
            # Call LLM to identify relevant packages
            llm_response = call_llm_for_task(
                task_name=TaskName.LOCALIZE,
                messages=messages,
                response_format=RelevantPackages
            )
            relevant_packages = llm_response.relevant_packages if llm_response else []
            logger.debug(f"Relevant Packages: {relevant_packages}")
        except Exception as e:
            logger.exception("Error calling LLM for relevant packages.")
            return []

        # Fetch detailed documentation for the identified packages
        package_details = self.project.fetch_package_details(relevant_packages[:top_n])

        # Generate the prompt for file localization
        messages = prompt_localize_to_files(issue, package_details)

        try:
            # Call LLM for file localization
            llm_response = call_llm_for_task(
                task_name=TaskName.LOCALIZE,
                messages=messages,
                response_format=FileLocalizationSuggestions
            )
            localization_suggestions = (
                llm_response.file_localization_suggestions if llm_response else []
            )
            logger.debug(f"File Localization Suggestions: {localization_suggestions}")
        except Exception as e:
            logger.exception("Error calling LLM for file localization.")
            return []

        # Extract file paths from localization suggestions
        return [
            self.get_file_path(suggestion)
            for suggestion in localization_suggestions
        ]

    def get_file_path(self, localization_suggestion: FileLocalizationSuggestion) -> str:
        """Generates the relative file path (in the repo) for a localization suggestion.

        Args:
            localization_suggestion (FileLocalizationSuggestion): A suggestion containing package and file info.

        Returns:
            str: The relative file path in the repository.
        """
        package = localization_suggestion.package.replace('.', os.sep)
        filename = localization_suggestion.file
        src_path = self.project.info.src_folder
        package_path = os.path.join(src_path, package) \
            if not package.startswith(src_path) \
            else package

        # Adjust path if package structure matches file name
        package_parts = package.split(os.sep)
        filename_without_ext, ext = os.path.splitext(filename)
        if package_parts[-1] == filename_without_ext:
            file_path = package_path + ext
        else:
            file_path = os.path.join(package_path, filename)

        return file_path