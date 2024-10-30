import json
import pytest

from se_agent.llm.model_configuration_manager import Configuration, TaskName

DEFAULT_MAX_TOKENS = 512

def test_add_provider():
    config = Configuration()
    config.add_provider("openai", "gpt-4o")
    assert "openai" in config.providers
    assert config.providers["openai"].default_model == "gpt-4o"
    assert config.providers["openai"].default_max_tokens == DEFAULT_MAX_TOKENS

def test_set_task_config():
    config = Configuration()
    config.add_provider("openai", "gpt-4o")
    config.set_task_config("openai", TaskName.GENERATE_CODE_SUMMARY, max_tokens=2000)
    task_config = config.get_task_config("openai", TaskName.GENERATE_CODE_SUMMARY)
    assert task_config.max_tokens == 2000
    assert task_config.model_name == "gpt-4o"

def test_get_task_config_default():
    config = Configuration()
    config.add_provider("openai", "gpt-4o")
    task_config = config.get_task_config("openai", TaskName.GENERATE_PACKAGE_SUMMARY)
    assert task_config.max_tokens == DEFAULT_MAX_TOKENS
    assert task_config.model_name == "gpt-4o"

def test_load_from_dict():
    config = Configuration()
    config_data = {
        "providers": {
            "openai": {
                "default_model": "gpt-4o",
                "default_max_tokens": 1500,
                "tasks": {
                    "generate_code_summary": {
                        "max_tokens": 2000
                    },
                    "localize": {
                        "max_tokens": 1500,
                        "model_name": "gpt-3.5-turbo"
                    }
                }
            }
        }
    }
    config.load_from_dict(config_data)
    assert "openai" in config.providers
    assert config.providers["openai"].default_model == "gpt-4o"
    assert config.providers["openai"].default_max_tokens == 1500
    task_config = config.get_task_config("openai", TaskName.GENERATE_CODE_SUMMARY)
    assert task_config.max_tokens == 2000
    assert task_config.model_name == "gpt-4o"
    task_config = config.get_task_config("openai", TaskName.LOCALIZE)
    assert task_config.max_tokens == 1500
    assert task_config.model_name == "gpt-3.5-turbo"

def test_load_from_yaml(tmp_path):
    config = Configuration()
    yaml_content = """
    providers:
      openai:
        default_model: "gpt-4o"
        default_max_tokens: 1500
        tasks:
          generate_code_summary:
            max_tokens: 2000
          localize:
            max_tokens: 1500
            model_name: "gpt-3.5-turbo"
    """
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml_content)
    config.load_from_yaml(str(yaml_file))
    assert "openai" in config.providers
    assert config.providers["openai"].default_model == "gpt-4o"
    assert config.providers["openai"].default_max_tokens == 1500
    task_config = config.get_task_config("openai", TaskName.GENERATE_CODE_SUMMARY)
    assert task_config.max_tokens == 2000
    assert task_config.model_name == "gpt-4o"

def test_load_from_json(tmp_path):
    config = Configuration()
    json_content = {
        "providers": {
            "openai": {
                "default_model": "gpt-4o",
                "default_max_tokens": 1500,
                "tasks": {
                    "generate_code_summary": {
                        "max_tokens": 2000
                    },
                    "localize": {
                        "max_tokens": 1500,
                        "model_name": "gpt-3.5-turbo"
                    }
                }
            }
        }
    }
    json_file = tmp_path / "config.json"
    json_file.write_text(json.dumps(json_content))
    config.load_from_json(str(json_file))
    assert "openai" in config.providers
    assert config.providers["openai"].default_model == "gpt-4o"
    assert config.providers["openai"].default_max_tokens == 1500
    task_config = config.get_task_config("openai", TaskName.GENERATE_CODE_SUMMARY)
    assert task_config.max_tokens == 2000
    assert task_config.model_name == "gpt-4o"

def test_load_from_yaml_file_not_found():
    config = Configuration()
    with pytest.raises(ValueError, match="YAML file 'non_existing_file.yaml' not found."):
        config.load_from_yaml("non_existing_file.yaml")

def test_load_from_json_file_not_found():
    config = Configuration()
    with pytest.raises(ValueError, match="JSON file 'non_existing_file.json' not found."):
        config.load_from_json("non_existing_file.json")

def test_load_from_yaml_parsing_error(tmp_path):
    config = Configuration()
    yaml_file = tmp_path / "invalid_config.yaml"
    yaml_file.write_text("invalid_yaml: [unclosed_list")
    with pytest.raises(ValueError, match="Error parsing YAML file '.*': .*"):
        config.load_from_yaml(str(yaml_file))

def test_load_from_json_parsing_error(tmp_path):
    config = Configuration()
    json_file = tmp_path / "invalid_config.json"
    json_file.write_text("{ invalid_json: }")
    with pytest.raises(ValueError, match="Error parsing JSON file '.*': .*"):
        config.load_from_json(str(json_file))
