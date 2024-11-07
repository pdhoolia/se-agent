import argparse
import os

from se_agent.project import Project
from se_agent.project_info import ProjectInfo
from se_agent.project_manager import ProjectManager

def onboard_agent():
    parser = argparse.ArgumentParser(description="Onboard a project (fork, clone, post-process a GitHub repo).")
    parser.add_argument("repo_full_name", type=str, help="Full name of the GitHub repo to fork (e.g., 'owner/repo').")
    parser.add_argument("src_folder", type=str, help="Path to the module source code in the repo. (e.g., 'module').")
    parser.add_argument("--api_url", type=str, help="Optional URL of the API server.")
    parser.add_argument("--github_token", type=str, help="Optional GitHub token for this specific project.")
    parser.add_argument("--main_branch", type=str, help="Optional main branch of the project (default: 'master').")

    args = parser.parse_args()
    github_token = args.github_token or os.getenv('GITHUB_TOKEN')
    main_branch = args.main_branch or os.getenv('MAIN_BRANCH')

    projects_store = os.getenv('PROJECTS_STORE')

    if not github_token or not projects_store:
        print("Environment variables GITHUB_TOKEN and PROJECTS_STORE must be set.")
        return

    # if projects_store folder doesn't exist, create it
    if not os.path.exists(projects_store):
        os.makedirs(projects_store)

    project_manager = ProjectManager(projects_store)
    project_info = project_manager.get_project(args.repo_full_name)
    
    if not project_info:
        # if you haven't alread added the project info to project.json
        project_info = ProjectInfo(repo_full_name=args.repo_full_name, src_folder=args.src_folder, api_url=args.api_url, github_token=github_token, main_branch=main_branch)
        project_manager.add_project(project_info)

    project = Project(github_token, projects_store, project_info)
    project.onboard()

if __name__ == "__main__":
    onboard_agent()