import os

from typing import Union

from langchain_ibm import WatsonxLLM
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel, BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    BaseMessage,
)
from se_agent.llm.model_configuration_manager import Configuration, TaskName
from se_agent.llm.retry_with_backoff import retry_with_exponential_backoff

def load_llm_config():
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

config = load_llm_config()
PROVIDER = os.getenv("LLM_PROVIDER_NAME")

def fetch_llm_for_task(task_name: TaskName, **kwargs) -> Union[BaseLanguageModel, BaseChatModel]:
    task_config = config.get_task_config(PROVIDER, task_name)
    
    if not task_config:
        raise ValueError(f"No task configuration found for provider: {PROVIDER}")
    
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
    else:
        raise ValueError(f"Unsupported LLM provider: {PROVIDER}")

def transform_to_langchain_base_chat_model_format(messages):
    """Transforms messages to Langchain chat prompt template format."""
    transformed_messages = []
    for message in messages:
        role = message['role']
        content = message['content']
        # Create corresponding Langchain message object based on role
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
    """Transforms a list of messages to a single prompt string."""
    prompt = "<|begin_of_text|>"
    for message in messages:
        role = message['role']
        content = message['content']
        prompt += f"<|start_header_id|>{role}<|end_header_id|>{content}<|eot_id|>"
    prompt += "<|start_header_id|>assistant<|end_header_id|>"
    return prompt

@retry_with_exponential_backoff
def call_llm_for_task(task_name: TaskName, messages: list, **kwargs):
    response_format = kwargs.pop('response_format', None)
    llm = fetch_llm_for_task(task_name, **kwargs)

    if response_format:
        if isinstance(llm, BaseChatModel):
            llm = llm.with_structured_output(response_format)
            return llm.invoke(transform_to_langchain_base_chat_model_format(messages))
        elif isinstance(llm, BaseLanguageModel):
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
