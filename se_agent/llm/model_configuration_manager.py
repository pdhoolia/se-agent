"""Module for managing LLM model configurations for various tasks.

This module provides classes and methods to define, manage, and retrieve configurations
for different tasks performed by language models. It supports defining task-specific 
configurations, loading configurations from YAML or JSON files, and retrieving default or 
task-specific settings for providers.
"""

import json
import yaml
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

DEFAULT_MAX_TOKENS = 512

class TaskName(Enum):
    """Enumeration of supported tasks for language models."""
    GENERATE_CODE_SUMMARY = "generate_code_summary"
    GENERATE_PACKAGE_SUMMARY = "generate_package_summary"
    GENERATE_REPO_SUMMARY = "generate_repo_summary"
    LOCALIZE = "localize"
    GENERATE_SUGGESTIONS = "generate_suggestions"
    EMBEDDING = "embedding"

@dataclass
class ModelConfig:
    """Configuration for a language model.

    Attributes:
        max_tokens (int): Maximum number of tokens to generate for the task.
        model_name (Optional[str]): The specific model name to use. Defaults to None.
    """
    max_tokens: int
    model_name: Optional[str] = None

@dataclass
class TaskConfig:
    """Configuration for a specific task.

    Attributes:
        task_name (TaskName): The name of the task.
        model_config (ModelConfig): The configuration of the model for this task.
    """
    task_name: TaskName
    model_config: ModelConfig

@dataclass
class ProviderConfig:
    """Configuration for a provider, including task-specific overrides.

    Attributes:
        provider_name (str): The name of the provider.
        default_model (str): The default model to use if not specified for a task.
        default_max_tokens (int): The default maximum token limit.
        tasks (Dict[TaskName, ModelConfig]): Task-specific model configurations.
    """
    provider_name: str
    default_model: str
    default_max_tokens: int = DEFAULT_MAX_TOKENS
    tasks: Dict[TaskName, ModelConfig] = field(default_factory=dict)

    def get_task_config(self, task_name: TaskName) -> ModelConfig:
        """Retrieve the model configuration for a given task.

        Args:
            task_name (TaskName): The task for which the configuration is needed.

        Returns:
            ModelConfig: The model configuration for the task.
        """
        if task_name in self.tasks:
            task_config = self.tasks[task_name]
            if task_config.model_name is None:
                task_config.model_name = self.default_model
            return task_config
        return ModelConfig(max_tokens=self.default_max_tokens, model_name=self.default_model)

class Configuration:
    """Manages provider and task configurations for language models.

    Attributes:
        providers (Dict[str, ProviderConfig]): A dictionary of provider configurations.
    """
    def __init__(self):
        self.providers: Dict[str, ProviderConfig] = {}

    def add_provider(self, provider_name: str, default_model: str, default_max_tokens: Optional[int] = None):
        """Adds a provider configuration.

        Args:
            provider_name (str): The name of the provider.
            default_model (str): The default model for the provider.
            default_max_tokens (Optional[int]): Default token limit. Defaults to None.
        """
        if default_max_tokens is None:
            default_max_tokens = DEFAULT_MAX_TOKENS
        self.providers[provider_name] = ProviderConfig(provider_name, default_model, default_max_tokens)

    def set_task_config(self, provider_name: str, task_name: TaskName, max_tokens: int, model_name: Optional[str] = None):
        """Sets a task-level configuration for a provider.

        Args:
            provider_name (str): The name of the provider.
            task_name (TaskName): The name of the task.
            max_tokens (int): The maximum tokens allowed for the task.
            model_name (Optional[str]): The specific model name for the task. Defaults to None.

        Raises:
            ValueError: If the provider is not configured.
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' is not configured. Available providers: {list(self.providers.keys())}")
        provider = self.providers[provider_name]
        provider.tasks[task_name] = ModelConfig(max_tokens=max_tokens, model_name=model_name)

    def get_task_config(self, provider_name: str, task_name: TaskName) -> ModelConfig:
        """Retrieves the configuration for a specific task under a provider.

        Args:
            provider_name (str): The name of the provider.
            task_name (TaskName): The task for which the configuration is needed.

        Returns:
            ModelConfig: The configuration for the task.

        Raises:
            ValueError: If the provider is not configured.
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' is not configured.")
        return self.providers[provider_name].get_task_config(task_name)

    def load_from_dict(self, config_data: Dict):
        """Loads configurations from a dictionary.

        Args:
            config_data (Dict): The configuration data.
        """
        for provider_name, provider_data in config_data.get("providers", {}).items():
            default_model = provider_data["default_model"]
            default_max_tokens = provider_data.get("default_max_tokens", DEFAULT_MAX_TOKENS)
            self.add_provider(provider_name, default_model, default_max_tokens)
            for task_name, task_data in provider_data.get("tasks", {}).items():
                max_tokens = task_data["max_tokens"]
                model_name = task_data.get("model_name")
                self.set_task_config(provider_name, TaskName(task_name), max_tokens, model_name)

    def load_from_yaml(self, yaml_file_path: str):
        """Loads configurations from a YAML file.

        Args:
            yaml_file_path (str): The path to the YAML file.

        Raises:
            ValueError: If the file is not found or there is a parsing error.
        """
        try:
            with open(yaml_file_path, "r") as file:
                config_data = yaml.safe_load(file)
        except FileNotFoundError:
            raise ValueError(f"YAML file '{yaml_file_path}' not found.")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file '{yaml_file_path}': {e}")
        self.load_from_dict(config_data)

    def load_from_json(self, json_file_path: str):
        """Loads configurations from a JSON file.

        Args:
            json_file_path (str): The path to the JSON file.

        Raises:
            ValueError: If the file is not found or there is a parsing error.
        """
        try:
            with open(json_file_path, "r") as file:
                config_data = json.load(file)
        except FileNotFoundError:
            raise ValueError(f"JSON file '{json_file_path}' not found.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON file '{json_file_path}': {e}")
        self.load_from_dict(config_data)