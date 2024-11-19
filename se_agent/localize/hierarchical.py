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

def prompt_identify_relevant_packages(issue: Dict[str, Any], package_summaries):
    """ Generates the prompt messages to identify relevant main packages. """

    messages = []

    # System message along with package summaries to reference, and instructions
    system_message = {
        'role': 'system',
        'content': """You are an AI assistant that helps with software issue localization.

You understand the issue content, any embedded code snippets, and any related discussion across messages.
Then based on the package summaries provided, you identify the most relevant packages and return a JSON formatted output as follows:"""
            + RELEVANT_PACKAGES_FORMAT_INSTRUCTIONS + 
f"""
Look at the following example for more guidance:

[EXAMPLE-START]

[PACKAGE-SUMMARIES-START]

# summarization

## Semantic Summary
The `summarization` package offers tools for summarization

## Contained code structure names
`summarizer1.py`, `summarizer2.py`, `generate_summary`

# retrieval

## Semantic Summary
The `retrieval` package offers a multitude of retrievers including keyword based (bm25: tf/idf), and semantic vector search based ...

## Contained code structure names
`retrieval.bm25`, `bm25_retriever.py`, `retrieve`, `retrieval.vectorized`, `vector_retriever`, `retrieve`

[PACKAGE-SUMMARIES-END]

[ISSUE-START]
Issue: fix vecotorized retrieval

Description:
This issue pertains to vectorized retrieval methods in the current system, which need optimization for large datasets.
[ISSUE-END]

Expected Output:
```json
{{
  "relevant_packages": ["retrieval"]
}}
```

[EXAMPLE-END]

Here are the actual package summaries:

[PACKAGE-SUMMARIES-START]
{package_summaries}
[PACKAGE-SUMMARIES-END]"""
    }
    messages.append(system_message)

    # The conversation from issue['conversation']. It includes the issue details and the ensuing conversation.
    conversation = issue.get('conversation', [])
    for message in conversation:
        # Map roles appropriately
        if message['role'] == 'user':
            role = 'user'
        else:
            role = 'assistant'
        messages.append({'role': role, 'content': message['content']})


    return messages

def prompt_localize_to_files(issue, package_details):
    """ Generates the prompt to localize issue to specific files and functions. """

    messages = []

    # System message along with relevant package details to reference, and instructions
    system_message = {
        "role": "system",
        "content": f"""You are an AI assistant that specializes in localizing issues to related files based on semantic summaries of code packages and files there-in.

You return the files that are most relevant to the issue in the following JSON format:

```json
{{
  "file_localization_suggestions": [
    {{
      "package": "<Fully qualified package name>",
      "file": "<Name of the Python file>",
      "confidence": <a floating point number between 0 and 1 with two decimal points indicating the confidence in the suggestion>,
      "reason": "<An explanation of the relevance of this file for the issue (not to exceed 50 tokens)>"
    }}
  ]
}}
```

Following are the semantic summaries of the files (and their containing packages) that you can refer to:
---
{package_details}
---

Semantic summaries above are in markdown format:
  - section headers for packages, sub-packages, and files.
  - File section header includes the extesion of the file.
  - package headers don't have any extension.
  - sub-package and file headers are nested under the package headers.
  - sub-package headers are qualified by the package headers.
  - to get the fully qualified package name for a file, just get the package header under which the file is nested.


DO NOT TRY TO SOLVE THE ISSUE. JUST LOCALIZE IT TO THE MOST RELEVANT FILES AND RETURN THE `file_localization_suggestions` JSON OBJECT as follows:
""" + FILE_LOCALIZATION_SUGGESTIONS_FORMAT_INSTRUCTIONS
    }
    messages.append(system_message)

    # The conversation from issue_analysis['conversation']. It includes the issue details and the ensuing conversation.
    conversation = issue.get('conversation', [])
    for message in conversation:
        # Map roles appropriately
        if message['role'] == 'user':
            role = 'user'
        else:
            role = 'assistant'
        messages.append({'role': role, 'content': message['content']})

    return messages

class HierarchicalLocalizationStrategy(LocalizationStrategy):
    def __init__(self, project: Project):
        self.project = project

    def localize(self, issue: Dict[str, str], top_n: int) -> List[str]:
        """
        Localizes the issue to specific files
        """
        # Determine top_n_packages from project configuration or default
        if self.project.info.top_n_packages:
            top_n = self.project.info.top_n_packages

        # Get package summaries
        package_summaries = self.project.fetch_package_summaries()

        # Generate the prompt to identify relevant packages
        messages = prompt_identify_relevant_packages(issue, package_summaries)

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
                logger.debug(f"Relevant Packages: {relevant_packages}")
            elif llm_response_relevant_packages.refusal:
                print(f"Refusal from LLM: {llm_response_relevant_packages.refusal}")
                return None
        except Exception as e:
            print(f"Error calling LLM for relevant packages: {e}")
            return None

        # Get detailed documentation for the identified packages
        package_details = self.project.fetch_package_details(relevant_packages[:top_n])

        # Generate the prompt for localization to files
        messages = prompt_localize_to_files(issue, package_details)

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
                logger.debug(f"File Localization Suggestions: {localization_suggestions}")
            elif llm_response_file_localization_suggestions.refusal:
                print(f"Refusal from LLM: {llm_response_file_localization_suggestions.refusal}")
                return None
        except Exception as e:
            print(f"Error calling LLM for localization: {e}")
            return None
        
        # Get the files being suggested
        filepaths = [
            self.get_file_path(suggestion)
            for suggestion in localization_suggestions
        ]
        
        return filepaths
    
    def get_file_path(self, localization_suggestion):
        """Get the file path for the localization suggestion."""
        package = localization_suggestion.package.replace('.', os.sep)
        filename = localization_suggestion.file
        src_path = self.project.info.src_folder
        if not package.startswith(src_path):
            package_path = os.path.join(src_path, package)
        else:
            package_path = package
        # Split the package by os.sep to check the last part of the package
        package_parts = package.split(os.sep)
        filename_without_extn, extn = os.path.splitext(filename)
        
        # Check if the last part of the package matches the filename (without extn)
        if package_parts[-1] == filename_without_extn:
            # The file should be located at x/y/z.extn instead of x/y/z/z.extn
            file_path = package_path + extn
        else:
            # Default behavior
            file_path = os.path.join(package_path, filename)
        
        return file_path