import os
import logging
from se_agent.project_manager import ProjectManager
from se_agent.project import Project

logger = logging.getLogger("se-agent-migration")

def migrate_existing_projects():
    projects_store = os.getenv('PROJECTS_STORE')
    github_token = os.getenv('GITHUB_TOKEN')
    project_manager = ProjectManager(projects_store)

    existing_projects = project_manager.list_projects()
    for project_info in existing_projects:
        try:
            project = Project(github_token, projects_store, project_info)
            project.build_vector_store_from_existing_summaries()
            logger.info(f"Successfully migrated project {project_info.repo_full_name}.")
        except Exception as e:
            logger.error(f"Failed to migrate project {project_info.repo_full_name}: {e}")

if __name__ == "__main__":
    migrate_existing_projects()