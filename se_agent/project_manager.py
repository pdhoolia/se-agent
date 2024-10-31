import json
import os
from typing import List, Optional

from se_agent.project import ProjectInfo

class ProjectManager:
    def __init__(self, projects_store_path):
        self.projects_store_path = projects_store_path
        self.projects_file = os.path.join(projects_store_path, 'projects.json')
        self.projects = self._load_projects()

    def _load_projects(self) -> List[ProjectInfo]:
        if not os.path.exists(self.projects_file):
            return []
        with open(self.projects_file, 'r') as f:
            projects_data = json.load(f)
        return [ProjectInfo(**proj) for proj in projects_data]

    def _save_projects(self):
        def to_dict(obj):
            return {k: v for k, v in obj.__dict__.items() if v is not None}

        with open(self.projects_file, 'w') as f:
            json.dump([to_dict(proj) for proj in self.projects], f, indent=2)

    def add_project(self, project_info: ProjectInfo):
        if self.get_project(project_info.repo_full_name):
            print(f"Project '{project_info.repo_full_name}' already exists.")
            return
        self.projects.append(project_info)
        self._save_projects()
        print(f"Added project '{project_info.repo_full_name}' to projects list.")

    def get_project(self, repo_full_name: str) -> Optional[ProjectInfo]:
        for proj in self.projects:
            if proj.repo_full_name == repo_full_name:
                return proj
        return None

    def list_projects(self) -> List[ProjectInfo]:
        return self.projects