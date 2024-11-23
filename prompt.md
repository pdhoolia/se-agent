You are an AI assistant that helps with software issue localization.

You understand the issue content, any embedded code snippets, and any related discussion across messages.
Then based on the package summaries provided, you identify the most relevant packages and return a JSON formatted output as follows:The output should be formatted as a JSON instance that conforms to the JSON schema below.

As an example, for the schema {"properties": {"foo": {"title": "Foo", "description": "a list of strings", "type": "array", "items": {"type": "string"}}}, "required": ["foo"]}
the object {"foo": ["bar", "baz"]} is a well-formatted instance of the schema. The object {"properties": {"foo": ["bar", "baz"]}} is not well-formatted.

Here is the output schema:
```
{"properties": {"relevant_packages": {"items": {"type": "string"}, "title": "Relevant Packages", "type": "array"}}, "required": ["relevant_packages"]}
```
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
{
  "relevant_packages": ["retrieval"]
}
```

[EXAMPLE-END]

Here are the actual package summaries:

[PACKAGE-SUMMARIES-START]
# localize

## Semantic Summary
The `localize` package offers a sophisticated framework for localizing software issues using advanced language model techniques, enhancing the efficiency of identifying and resolving software bugs. It incorporates a hierarchical localization strategy, abstract localization methods, and a semantic vector search approach to determine relevant packages and files. By leveraging structured prompts and semantic vector databases, it enables precise issue localization, thus streamlining the maintenance workflow in software projects.

## Contained code structure names
`hierarchical.py`, `RelevantPackages`, `FileLocalizationSuggestion`, `FileLocalizationSuggestions`, `prompt_identify_relevant_packages`, `prompt_localize_to_files`, `HierarchicalLocalizationStrategy`, `localization_strategy.py`, `LocalizationStrategy`, `LocalizationStrategyType`, `VectorType`, `semantic_vector_search.py`, `SemanticVectorSearchLocalization`, `_get_vector_store`, `add_documents`, `add_document`, `delete_documents`, `localize`

# migrate

## Semantic Summary
The `migrate` package facilitates the transition of existing projects to a new setup by creating vector stores from project summaries. It leverages environment variables for configuration and ensures a comprehensive logging mechanism to track the migration process. This package is critical for developers looking to systematically organize and manage project data by summarizing and structuring it in a more efficient format, thereby enhancing data storage and retrieval capabilities.

## Contained code structure names
`create_vector_stores.py`, `migrate_existing_projects`

# repository_analyzer

## Semantic Summary
The `repository_analyzer` package offers tools for analyzing Python code repositories through semantic descriptions and summaries. It leverages language models to generate meaningful insights into Python files and packages, facilitating a deeper understanding of code structures and documentation. By providing mechanisms to describe individual files and summarize entire packages, this package aids developers in efficiently navigating and comprehending complex codebases.

## Contained code structure names
`file_analyzer.py`, `package_summary.py`, `prompt_generate_semantic_description`, `generate_semantic_description`, `prompt_generate_package_summary`, `generate_package_summary`

# se_agent

## Semantic Summary
The `se_agent` package provides a robust framework for managing software projects via GitHub, focusing on issue analysis, code change suggestions, and project onboarding. It leverages AI-driven tools to automate the localization and resolution of software issues, enhance project documentation, and facilitate seamless project management. Key components include a Flask server for handling webhooks, a change suggestion engine using language models, and a comprehensive project management system with GitHub integration and semantic code understanding.

## Contained code structure names
`__init__.py`, `change_suggester.py`, `flask_server.py`, `issue_analyzer.py`, `listener_core.py`, `localizer.py`, `onboard_agent.py`, `project.py`, `project_info.py`, `project_manager.py`, `logger`, `suggest_changes`, `onboard_project_route`, `webhook_route`, `analyze_issue`, `process_webhook`, `LocalizationStrategyType`, `ProjectManager`, `Project`, `ProjectInfo`, `RelevantPackages`, `FileLocalizationSuggestion`, `localize_issue`, `onboard_agent`, `clone_repository`, `update_codebase_understanding`, `fetch_package_summaries`, `post_issue_comment`, `ProjectManager`, `add_project`, `get_project`.

# llm

## Semantic Summary
The `llm` package is designed to configure, manage, and utilize language models and embeddings from various providers for diverse tasks such as chat responses and embeddings. It provides robust configuration management through data classes and enumerations, supporting JSON and YAML formats for defining task-specific models. The package also includes a retry mechanism for function executions using exponential backoff, enhancing reliability in network-related operations or API calls. Key functionalities involve loading configurations, fetching models, transforming message formats, and executing tasks with error handling.

## Contained code structure names
`api.py`, `load_llm_config`, `fetch_llm_for_task`, `fetch_embedding_model`, `transform_to_langchain_base_chat_model_format`, `transform_to_base_language_model_single_prompt_string`, `call_llm_for_task`, `model_configuration_manager.py`, `TaskName`, `ModelConfig`, `TaskConfig`, `ProviderConfig`, `Configuration`, `get_task_config`, `add_provider`, `set_task_config`, `load_from_dict`, `load_from_yaml`, `load_from_json`, `retry_with_backoff.py`, `retry_with_exponential_backoff`

# lambda

## Semantic Summary
The `lambda` package provides an AWS Lambda function designed to handle onboarding and GitHub webhook events. It processes HTTP requests by method and path, leveraging separate functions for specific tasks such as onboarding and webhook processing. The package incorporates environment management, JSON data handling, and logging for efficient event tracking and debugging.

## Contained code structure names
`lambda_function.py`, `handler`, `onboard_project`, `process_webhook`, `os`, `dotenv`, `json`, `logging`

# util

## Semantic Summary
The `util` package provides utility scripts for file and directory management and text processing in Python. It includes tools for recursively counting files and folders within directories, with options for filtering by file extension and handling errors gracefully. Additionally, it offers functionality for extracting content from markdown code blocks using regular expressions. The package is designed to offer simple command-line interfaces for user interaction, making it accessible for both script-based and interactive use cases.

## Contained code structure names
`file_count.py`, `count_files_in_folder_recursive`, `folder_count.py`, `count_folders_in_folder_recursive`, `markdown.py`, `extract_code_block_content`


[PACKAGE-SUMMARIES-END]'