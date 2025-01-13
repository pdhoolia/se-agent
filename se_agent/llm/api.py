"""Module for managing interactions with LLMs (Language Learning Models).

This module provides functionality to load configurations, fetch models, transform input messages,
and call LLMs for various tasks, including embeddings and chat-based interactions. It supports 
multiple providers like OpenAI, Watsonx, Ollama, and HuggingFace.
"""

import os
from typing import Union

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseLanguageModel, BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ibm import WatsonxLLM
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from se_agent.llm.model_configuration_manager import Configuration, TaskName
from se_agent.llm.retry_with_backoff import retry_with_exponential_backoff


def load_llm_config():
    """Loads the LLM configuration from a file specified in environment variables.

    The configuration file can be either YAML or JSON format.

    Returns:
        Configuration: The loaded configuration instance.

    Raises:
        ValueError: If the configuration file path is not set or is in an unsupported format.
    """
    config_file_path = os.getenv("LLM_CONFIG_FILE_PATH")
    
    if not config_file_path:
        raise ValueError("LLM_CONFIG_FILE_PATH is not set in the environment variables")
    
    config = Configuration()
    if config_file_path.endswith(".yaml"):
        config.load_from_yaml(config_file_path)
    elif config_file_path.endswith(".json"):
        config.load_from_json(config_file_path)
    else:
        raise ValueError("Unsupported configuration file format. Use .yaml or .json")
    
    return config


# Global configuration for the module
config = load_llm_config()
PROVIDER = os.getenv("LLM_PROVIDER_NAME")


def fetch_llm_for_task(task_name: TaskName, **kwargs) -> Union[BaseLanguageModel, BaseChatModel, Embeddings]:
    """Fetches the appropriate LLM or embedding model for a given task.

    Args:
        task_name (TaskName): The name of the task for which the LLM is required.
        **kwargs: Additional arguments for initializing the model.

    Returns:
        Union[BaseLanguageModel, BaseChatModel, Embeddings]: The initialized model.

    Raises:
        ValueError: If no configuration exists for the task or if the provider is unsupported.
    """
    task_config = config.get_task_config(PROVIDER, task_name)
    
    if not task_config:
        raise ValueError(f"No task configuration found for provider: {PROVIDER}")
    
    if task_name == TaskName.EMBEDDING:
        return fetch_embedding_model(task_config.model_name)
    
    model_name = task_config.model_name
    max_tokens = task_config.max_tokens
    
    if PROVIDER == "openai":
        return ChatOpenAI(model=model_name, max_tokens=max_tokens, **kwargs)
    elif PROVIDER == "watsonx":
        return WatsonxLLM(
            model_id=model_name,
            project_id=os.getenv("WATSONX_PROJECT_ID"),
            url=os.getenv("WATSONX_URL"),
            apikey=os.getenv("WATSONX_APIKEY"),
            params={"decoding_method": "greedy", "max_new_tokens": max_tokens},
        )
    elif PROVIDER == "ollama":
        return OllamaLLM(model=model_name, max_tokens=max_tokens, **kwargs)
    else:
        raise ValueError(f"Unsupported LLM provider: {PROVIDER}")


def fetch_embedding_model(model_name: str) -> Embeddings:
    """Fetches the embedding model based on the provider.

    Args:
        model_name (str): The name of the embedding model.

    Returns:
        Embeddings: The initialized embedding model.

    Raises:
        ValueError: If the provider is unsupported.
    """
    if PROVIDER == "openai":
        return OpenAIEmbeddings(model=model_name)
    elif PROVIDER == "ollama":
        return OllamaEmbeddings(model=model_name)
    elif PROVIDER == "watsonx":
        return HuggingFaceEmbeddings(model_name=model_name)
    else:
        raise ValueError(f"Unsupported embedding provider: {PROVIDER}")


def transform_to_langchain_base_chat_model_format(messages):
    """Transforms a list of messages into the Langchain BaseChatModel format.

    Args:
        messages (list): A list of dictionaries with keys `role` and `content`.

    Returns:
        list: A list of Langchain message objects (HumanMessage, SystemMessage, AIMessage).

    Raises:
        ValueError: If an unknown role is encountered in the messages.
    """
    transformed_messages = []
    for message in messages:
        role = message['role']
        content = message['content']
        if role == 'user':
            transformed_message = HumanMessage(content=content)
        elif role == 'assistant':
            transformed_message = AIMessage(content=content)
        elif role == 'system':
            transformed_message = SystemMessage(content=content)
        else:
            raise ValueError(f"Unknown role: {role}")
        transformed_messages.append(transformed_message)
    return transformed_messages


def transform_to_base_language_model_single_prompt_string(messages):
    """Transforms a list of messages into a single string prompt for language models.

    Args:
        messages (list): A list of dictionaries with keys `role` and `content`.

    Returns:
        str: A single prompt string formatted for base language models.
    """
    prompt = "<|begin_of_text|>"
    for message in messages:
        role = message['role']
        content = message['content']
        prompt += f"<|start_header_id|>{role}<|end_header_id|>{content}<|eot_id|>"
    prompt += "<|start_header_id|>assistant<|end_header_id|>"
    return prompt


@retry_with_exponential_backoff
def call_llm_for_task(task_name: TaskName, messages: list, **kwargs):
    """Calls the LLM for a specific task with the given messages and optional parameters.

    Args:
        task_name (TaskName): The name of the task to perform.
        messages (list): A list of messages to provide as input to the LLM.
        **kwargs: Additional arguments, including:
            - response_format (Optional): A pydantic class for structured output.

    Returns:
        Union[BaseMessage, AIMessage, Any]: The response from the LLM.

    Raises:
        ValueError: If the response type is unsupported.
    """
    response_format = kwargs.pop('response_format', None)
    llm = fetch_llm_for_task(task_name, **kwargs)

    if response_format:
        if isinstance(llm, BaseChatModel):
            llm = llm.with_structured_output(response_format)
            return llm.invoke(transform_to_langchain_base_chat_model_format(messages))
        elif isinstance(llm, BaseLanguageModel) or PROVIDER in ["watsonx", "ollama"]:
            parser = PydanticOutputParser(pydantic_object=response_format)
            chain = llm | parser
            return chain.invoke(input=transform_to_base_language_model_single_prompt_string(messages))
    else:
        if isinstance(llm, BaseChatModel):
            return llm.invoke(transform_to_langchain_base_chat_model_format(messages))
        elif isinstance(llm, BaseLanguageModel):
            response = llm.invoke(input=transform_to_base_language_model_single_prompt_string(messages))
            if isinstance(response, str):
                return AIMessage(content=response)
            elif isinstance(response, BaseMessage):
                return response
            else:
                raise ValueError(f"Unsupported response type: {type(response)}")
