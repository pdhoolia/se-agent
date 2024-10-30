from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ProjectInfo:
    repo_full_name: str                                     # e.g., 'conversational-ai/se-agent'
    src_folder: str                                         # e.g., 'se_agent'
    api_url: Optional[str] = field(default=None)            # e.g., 'https://github.ibm.com/api/v3'
    github_token: Optional[str] = field(default=None)       # GitHub token for the project
    main_branch: Optional[str] = field(default="master")    # e.g., 'main'
    top_n_packages: Optional[int] = field(default=None)     # Custom top_n_packages for the project
    top_n_files: Optional[int] = field(default=None)        # Custom top_n_files for the project