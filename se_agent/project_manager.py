"""Module for managing projects, including loading, saving, adding, and retrieving project information."""

import json
import logging
import os
from typing import List, Optional

from se_agent.project import ProjectInfo

logger = logging.getLogger("se-agent")

class ProjectManager:
    """Manages projects by loading from and saving to a JSON file.

    Attributes:
        projects_store_path (str): The directory where projects are stored.
        projects_file (str): The file path to the projects JSON file.
        projects (List[ProjectInfo]): The list of loaded projects.
    """
    def __init__(self, projects_store_path):
        """Initializes the ProjectManager.

        Args:
            projects_store_path (str): The directory where projects are stored.
        """
        self.projects_store_path = projects_store_path
        self.projects_file = os.path.join(projects_store_path, 'projects.json')
        self.projects = self._load_projects()

    def _load_projects(self) -> List[ProjectInfo]:
        """Loads projects from the projects JSON file.

        Returns:
            List[ProjectInfo]: A list of loaded ProjectInfo objects.
        """
        if not os.path.exists(self.projects_file):
            return []
        with open(self.projects_file, 'r') as f:
            projects_data = json.load(f)
        return [ProjectInfo(**proj) for proj in projects_data]

    def _save_projects(self):
        """Saves the current list of projects to the projects JSON file."""

        def to_dict(obj):
            """Converts an object to a dictionary, excluding None values.

            Args:
                obj: The object to convert.

            Returns:
                dict: A dictionary representation of the object.
            """
            return {k: v for k, v in obj.__dict__.items() if v is not None}

        with open(self.projects_file, 'w') as f:
            json.dump([to_dict(proj) for proj in self.projects], f, indent=2)

    def add_project(self, project_info: ProjectInfo):
        """Adds a new project to the projects list.

        Args:
            project_info (ProjectInfo): The project information to add.
        """
        if self.get_project(project_info.repo_full_name):
            logger.debug(f"Project '{project_info.repo_full_name}' already exists.")
            return
        self.projects.append(project_info)
        self._save_projects()
        logger.debug(f"Added project '{project_info.repo_full_name}' to projects list.")

    def get_project(self, repo_full_name: str) -> Optional[ProjectInfo]:
        """Retrieves a project by its repository full name.

        Args:
            repo_full_name (str): The full repository name.

        Returns:
            Optional[ProjectInfo]: The matching ProjectInfo or None if not found.
        """
        for proj in self.projects:
            if proj.repo_full_name == repo_full_name:
                return proj
        return None

    def list_projects(self) -> List[ProjectInfo]:
        """Lists all the projects.

        Returns:
            List[ProjectInfo]: A list of all ProjectInfo objects.
        """
        return self.projects