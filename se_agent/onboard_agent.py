"""Script for onboarding a project by cloning and processing a GitHub repository."""

import argparse
import os

from se_agent.project import Project
from se_agent.project_info import ProjectInfo
from se_agent.project_manager import ProjectManager

def onboard_agent():
    """Onboards a project by parsing arguments and initializing project components.

    Parses command-line arguments to get repository information, checks for required
    environment variables, initializes project configurations, and initiates the
    onboarding process.

    Raises:
        SystemExit: If required environment variables are not set.
    """
    parser = argparse.ArgumentParser(
        description="Onboard a project (fork, clone, post-process a GitHub repo)."
    )
    parser.add_argument(
        "repo_full_name",
        type=str,
        help="Full name of the GitHub repo to fork (e.g., 'owner/repo')."
    )
    parser.add_argument(
        "src_folder",
        type=str,
        help="Path to the module source code in the repo (e.g., 'module')."
    )
    parser.add_argument(
        "--api_url",
        type=str,
        help="Optional URL of the API server."
    )
    parser.add_argument(
        "--github_token",
        type=str,
        help="Optional GitHub token for this specific project."
    )
    parser.add_argument(
        "--main_branch",
        type=str,
        help="Optional main branch of the project (default: 'master')."
    )

    # Parse command-line arguments
    args = parser.parse_args()
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')
    main_branch = args.main_branch or os.getenv('MAIN_BRANCH')
    projects_store = os.getenv('PROJECTS_STORE')

    # Check for required environment variables
    if not github_token or not projects_store:
        print("Environment variables GITHUB_TOKEN and PROJECTS_STORE must be set.")
        return

    # Create the projects store directory if it doesn't exist
    if not os.path.exists(projects_store):
        os.makedirs(projects_store)

    # Initialize the project manager
    project_manager = ProjectManager(projects_store)
    project_info = project_manager.get_project(args.repo_full_name)
    
    if not project_info:
        # Add the project info to projects.json if it doesn't already exist
        project_info = ProjectInfo(
            repo_full_name=args.repo_full_name,
            src_folder=args.src_folder,
            api_url=args.api_url,
            github_token=github_token,
            main_branch=main_branch
        )
        project_manager.add_project(project_info)

    # Initialize the Project and start the onboarding process
    project = Project(github_token, projects_store, project_info)
    project.onboard()

if __name__ == "__main__":
    onboard_agent()