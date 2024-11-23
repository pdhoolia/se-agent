"""Script for migrating existing projects by building vector stores from their semantic summaries."""

import os
import logging
from se_agent.project_manager import ProjectManager
from se_agent.project import Project

# Configure logger for migration process
logger = logging.getLogger("se-agent-migration")

def migrate_existing_projects():
    """Migrates existing projects by creating vector stores from their existing semantic summaries.

    This script retrieves the list of projects managed by the ProjectManager,
    iterates through them, and for each project, invokes the method to build
    a vector store using existing semantic summaries.

    Logs the success or failure of the migration for each project.
    """
    # Retrieve required environment variables
    projects_store = os.getenv('PROJECTS_STORE')
    github_token = os.getenv('GITHUB_TOKEN')

    # Initialize the ProjectManager
    project_manager = ProjectManager(projects_store)

    # Retrieve the list of existing projects
    existing_projects = project_manager.list_projects()

    for project_info in existing_projects:
        try:
            # Initialize the project and build its vector store
            project = Project(github_token, projects_store, project_info)
            project.build_vector_store_from_existing_summaries()
            logger.info(f"Successfully migrated project {project_info.repo_full_name}.")
        except Exception as e:
            # Log any errors encountered during migration
            logger.error(f"Failed to migrate project {project_info.repo_full_name}: {e}")

if __name__ == "__main__":
    # Execute the migration process
    migrate_existing_projects()