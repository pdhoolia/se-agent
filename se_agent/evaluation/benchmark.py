import argparse
import logging
import os
import json
from datasets import load_dataset

from se_agent.evaluation.evaluate import evaluate
from se_agent.project import Project
from se_agent.project_info import ProjectInfo
from se_agent.project_manager import ProjectManager

logger = logging.getLogger("se-agent")

def run(dataset_uri: str, split: str):
    # Load the SWE-bench-lite dataset
    benchmark = load_dataset(dataset_uri, split=split)
    logger.info(f"Loaded benchmark dataset: {benchmark}")

    # Evaluate the se-agent on the benchmark dataset
    for issue in benchmark.to_list()[:1]:
        repo = issue.get("repo")
        instance_id = issue.get('instance_id')
        base_commit = issue.get('base_commit')
        problem_statement = issue.get('problem_statement')
        
        logger.info(f"Running se-agent on: {instance_id} | {repo} | {base_commit} | {problem_statement[:50]}...")

        # Try get project info for the repo
        project_info = project_manager.get_project(repo)
        project = None
        # let's create and add if we don't have it in our projects store
        if not project_info:
            # Use the repo_src_mapping to get the source folder for the repo
            src_folder = repo_src_mapping.get(repo, repo.split('/')[1])
            project_info = ProjectInfo(
                repo_full_name=repo,
                src_folder=src_folder,
                github_token=os.getenv('GITHUB_TOKEN'),
                main_branch=os.getenv('MAIN_BRANCH')
            )
            project_manager.add_project(project_info)
            
        # initialize the project
        project = Project(project_info.github_token, projects_store, project_info)
        if not project.is_cloned():
            # clone the repo
            project.clone_repository(requires_safe_directory=False, requires_auth=False)

        # Evaluate the se-agent on the issue
        evaluate(project, instance_id, problem_statement, base_commit)

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Run the se-agent on a benchmark dataset.")
    parser.add_argument("dataset_uri", type=str, help="URI of the benchmark dataset to run the se-agent on.")
    parser.add_argument("split", type=str, help="Split of the dataset to run the se-agent on.")
    
    args = parser.parse_args()

    projects_store = os.getenv('PROJECTS_STORE')
    project_manager = ProjectManager(projects_store)

    # Load the swe-bench-repo-src.json file as a dictionary
    repo_src_mapping_path = 'swe-bench-repo-src.json'
    with open(repo_src_mapping_path, 'r') as f:
        repo_src_mapping = json.load(f)
    logger.info(f"Loaded repository-source folder mapping: {repo_src_mapping_path}")
    
    run(args.dataset_uri, args.split)