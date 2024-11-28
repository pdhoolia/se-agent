import logging
import os
from se_agent.change_suggester import suggest_changes
from se_agent.llm.api import fetch_llm_for_task
from se_agent.llm.model_configuration_manager import TaskName
from se_agent.localize.semantic_vector_search import SemanticVectorSearchLocalizer
from se_agent.project import Project
from se_agent.project_info import ProjectInfo
from se_agent.util.vector_store_utils import VectorType, create_or_update_vector_store, get_vector_store

logger = logging.getLogger("se-agent")
TOP_N = 5
LOG_MSG_LENGTH = 200  # Maximum str length of log messages

def evaluate(repo_full_name: str, instance_id: str, problem_statement: str, base_commit: str="HEAD"):
    """
    Evaluates the se-agent for a given task instance using the SWE-bench dataset.

    This method sets up a project from a pre-cloned repository, resets it to a specific
    commit, and then performs localization and change suggestion tasks. It stores the
    results in a designated evaluation directory.

    Args:
        repo_full_name (str): The full name of the repository (e.g., "owner/repo").
        instance_id (str): The unique identifier for the evaluation task instance.
        problem_statement (str): The problem statement or issue body to be evaluated.
        base_commit (str): The commit hash on which the problem statement is based. Defaults to "HEAD".

    Steps:
        1. Initialize a Project instance with the provided repository information.
        2. Reset the repository to the specified commit hash.
        3. Create an evaluation directory under the project's metadata folder.
        4. Create a vector store for the code at the specified commit.
        5. Use SemanticVectorSearchLocalizer to localize relevant files.
        6. Generate change suggestions based on the localization results.
        7. Dump the change suggestions to a markdown file in the evaluation directory.
        8. Reset the repository back to the HEAD of the main branch.

    Raises:
        Exception: Propagates any exceptions encountered during the evaluation process.
    """
    projects_store = os.getenv('PROJECTS_STORE')
    github_token = os.getenv('GITHUB_TOKEN')
    provider = os.getenv('LLM_PROVIDER_NAME')
    vector_type = VectorType.CODE.value
    
    # Create ProjectInfo and Project instance
    project_info = ProjectInfo(repo_full_name=repo_full_name, src_folder='se_agent', github_token=github_token)
    project = Project(github_token, projects_store, project_info)

    # Get current commit hash (to reset back later)
    current_commit = project.get_current_commit()

    # Reset repo to the specified commit hash
    project.reset_to_commit(base_commit)

    # Prepare evaluation directory
    evaluation_folder = os.path.join(project.metadata_folder, 'evaluation')
    os.makedirs(evaluation_folder, exist_ok=True)
    logger.info(f"Evaluation folder: {evaluation_folder}")

    # Create (or load from cache) a vector store for the specific commit
    vector_store_uri = os.path.join(evaluation_folder, f'{base_commit[:7]}_{provider[:1]}_{vector_type[:1]}_vs.db')
    logger.info(f"Vector store URI: {vector_store_uri}")
    embeddings = fetch_llm_for_task(TaskName.EMBEDDING)
    if not os.path.exists(vector_store_uri):
        vector_store = create_or_update_vector_store(project.module_src_folder, vector_store_uri, embeddings, path_prefix=project_info.src_folder)
        logger.info(f"Vector store created at: {vector_store_uri}")
    else:
        vector_store = get_vector_store(embeddings, vector_store_uri)

    # Create a SemanticVectorSearchLocalizer with this vector store
    localizer = SemanticVectorSearchLocalizer(vector_store)

    # format issue as expected
    issue={'conversation': [{'role': 'user', 'content': problem_statement}]}

    # Localize and suggest changes
    filepaths = localizer.localize(issue=issue, top_n=TOP_N)
    logger.debug(f"Localization results: {filepaths}")
    change_suggestions = suggest_changes(project, issue, filepaths)
    logger.debug(f"Change suggestions: {change_suggestions[:LOG_MSG_LENGTH]}{'...' if len(change_suggestions) > LOG_MSG_LENGTH else ''}")

    # Dump change suggestions to a file
    change_suggestions_path = os.path.join(evaluation_folder, f'{instance_id}_change_suggestions.md')
    with open(change_suggestions_path, 'w') as f:
        f.write(change_suggestions)
    logger.info(f"Change suggestions saved to: {change_suggestions_path}")

    # Reset the repo back to original commit
    project.reset_to_commit(current_commit)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate the se-agent for a given task instance using the SWE-bench dataset.")
    parser.add_argument("repo_full_name", type=str, help="Full name of the GitHub repo to evaluate (e.g., 'owner/repo').")
    parser.add_argument("instance_id", type=str, help="Unique identifier for the evaluation task instance.")
    parser.add_argument("problem_filepath", type=str, help="Path to the file containing the problem statement.")
    parser.add_argument("--base_commit", type=str, default="HEAD", help="Commit hash on which the problem statement is based.")

    args = parser.parse_args()
    with open(args.problem_filepath, 'r') as f:
        problem_statement = f.read()
    evaluate(args.repo_full_name, args.instance_id, problem_statement, args.base_commit)
