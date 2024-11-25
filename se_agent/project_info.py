"""Manages project level configurations and settings. Agent configurations that may be overridden at project level are declared here."""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ProjectInfo:
    """Represents project information, configurations, and settings.

    Attributes:
        repo_full_name (str): The full repository name (e.g., 'conversational-ai/se-agent').
        src_folder (str): The source folder name (e.g., 'se_agent').
        api_url (Optional[str]): The API URL (e.g., 'https://github.ibm.com/api/v3'). Defaults to None.
        github_token (Optional[str]): GitHub token for the project. Defaults to None.
        main_branch (Optional[str]): The main branch name (e.g., 'master'). Defaults to 'main'.
        top_n_packages (Optional[int]): Custom top_n_packages for the project. Defaults to None.
        top_n_files (Optional[int]): Custom top_n_files for the project. Defaults to None.
        preferred_vector_type (str): The preferred vector type for the project. Defaults to DEFAULT_VECTOR_TYPE.
    """
    repo_full_name: str
    src_folder: str
    api_url: Optional[str] = field(default=None)
    github_token: Optional[str] = field(default=None)
    main_branch: Optional[str] = field(default="main")
    top_n_packages: Optional[int] = field(default=None)
    top_n_files: Optional[int] = field(default=None)
    preferred_vector_type: Optional[str] = field(default=None)