import json
import yaml
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

DEFAULT_MAX_TOKENS = 512

# let's create an enum for various tasks
class TaskName(Enum):
    GENERATE_CODE_SUMMARY = "generate_code_summary"
    GENERATE_PACKAGE_SUMMARY = "generate_package_summary"
    GENERATE_REPO_SUMMARY = "generate_repo_summary"
    LOCALIZE = "localize"
    GENERATE_SUGGESTIONS = "generate_suggestions"

@dataclass
class ModelConfig:
    max_tokens: int
    model_name: Optional[str] = None

@dataclass
class TaskConfig:
    task_name: TaskName
    model_config: ModelConfig

@dataclass
class ProviderConfig:
    provider_name: str
    default_model: str
    default_max_tokens: int = DEFAULT_MAX_TOKENS
    tasks: Dict[TaskName, ModelConfig] = field(default_factory=dict)

    def get_task_config(self, task_name: TaskName) -> ModelConfig:
        """
        Retrieve the model configuration for a given task.
        """
        if task_name in self.tasks:
            task_config = self.tasks[task_name]
            # If model_name is None, use the provider's default model
            if task_config.model_name is None:
                task_config.model_name = self.default_model
            return task_config
        else:
            # Return default configuration if task is not set
            return ModelConfig(max_tokens=self.default_max_tokens, model_name=self.default_model)

class Configuration:
    def __init__(self):
        self.providers: Dict[str, ProviderConfig] = {}

    def add_provider(self, provider_name: str, default_model: str, default_max_tokens: Optional[int] = None):
        if default_max_tokens is None:
            default_max_tokens = DEFAULT_MAX_TOKENS
        self.providers[provider_name] = ProviderConfig(provider_name, default_model, default_max_tokens)

    def set_task_config(self, provider_name: str, task_name: TaskName, max_tokens: int, model_name: Optional[str] = None):
        """
        Set a task-level configuration for a specific provider.
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' is not configured. Available providers: {list(self.providers.keys())}")
        provider = self.providers[provider_name]
        if task_name in provider.tasks:
            print(f"Warning: Overwriting existing task configuration for '{task_name}' in provider '{provider_name}'")
        provider.tasks[task_name] = ModelConfig(max_tokens=max_tokens, model_name=model_name)

    def get_task_config(self, provider_name: str, task_name: TaskName) -> ModelConfig:
        """
        Get the task configuration for a specific provider and task.
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' is not configured.")
        return self.providers[provider_name].get_task_config(task_name)

    def load_from_dict(self, config_data: Dict):
        """
        Load configuration from a dictionary.
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
        """
        Load configuration from a YAML file.
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
        """
        Load configuration from a JSON file.
        """
        try:
            with open(json_file_path, "r") as file:
                config_data = json.load(file)
        except FileNotFoundError:
            raise ValueError(f"JSON file '{json_file_path}' not found.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error parsing JSON file '{json_file_path}': {e}")
        self.load_from_dict(config_data)