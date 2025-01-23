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

        # Fetch package summaries and a list of packages from the project
        package_summaries, package_list = self.project.fetch_package_summaries()

        # If there's only one package, skip LLM call for package identification
        relevant_packages = package_list if len(package_list) == 1 else []

        if not relevant_packages:
            # Generate the prompt for identifying relevant packages
            messages = prompt_identify_relevant_packages(issue, package_summaries)

            try:
                # Call LLM to identify relevant packages
                llm_response = call_llm_for_task(
                    task_name=TaskName.LOCALIZE,
                    messages=messages,
                    response_format=RelevantPackages
                )
                llm_relevant_packages = llm_response.relevant_packages if llm_response else []
                logger.debug(f"LLM returned relevant packages: {llm_relevant_packages}")
                # Apply fuzziness to map LLM response to actual package names
                relevant_packages = self.apply_fuzziness_to_packages(llm_relevant_packages, package_list)
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
            file_path
            for suggestion in localization_suggestions
            if (file_path := self.fuzzy_get_file_path(suggestion))  # Filters out empty strings
        ]

    def apply_fuzziness_to_packages(self, llm_packages: List[str], actual_packages: List[str]) -> List[str]:
        """Applies fuzziness to map LLM identified packages to actual package names.

        Args:
            llm_packages (List[str]): Packages identified by LLM.
            actual_packages (List[str]): Actual packages in the project.

        Returns:
            List[str]: Mapped list of actual package names.
        """
        mapped_packages = []
        for llm_package in llm_packages:
            # Normalize LLM package response
            normalized_llm_package = llm_package.replace('/', '.').replace('.py', '')

            # Direct match or fuzzy match
            for actual_package in actual_packages:
                if  normalized_llm_package == actual_package or \
                normalized_llm_package.endswith(actual_package.split('.')[-1]):
                    mapped_packages.append(actual_package)
                    break

            # Fuzzy match using filename to package mapping
            filename = llm_package.split('/')[-1]
            package_from_filename = self.project.get_package(filename)
            if package_from_filename:
                mapped_packages.add(package_from_filename)

        return mapped_packages

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
    
    def fuzzy_get_file_path(self, localization_suggestion: FileLocalizationSuggestion) -> str:
        """Fuzzily validates and corrects the file path for a localization suggestion.

        Args:
            localization_suggestion (FileLocalizationSuggestion): A suggestion containing package and file info.

        Returns:
            str: The corrected relative file path in the repository.
        """
        # Initial file path from the standard logic
        file_path = self.get_file_path(localization_suggestion)

        # Check if the file_path exists
        if os.path.exists(os.path.join(self.project.repo_folder, file_path)):
            return file_path

        # If the file_path does not exist, attempt fuzzy correction
        logger.debug(f"File path '{file_path}' does not exist. Attempting fuzzy correction.")

        # Get the filename from the suggestion
        filename = localization_suggestion.file

        # Search for the file in the source folder, ignoring package structure
        for root, _, files in os.walk(self.project.module_src_folder):
            if filename in files:
                # Reconstruct the relative path
                corrected_file_path = os.path.join(os.path.relpath(root, start=self.project.repo_folder), filename)
                logger.debug(f"Fuzzily corrected file path to '{corrected_file_path}'.")
                return corrected_file_path

        # If no match is found, log and return an empty string
        logger.warning(f"Unable to fuzzily correct file path for '{filename}'.")
        return ""