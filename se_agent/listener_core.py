"""Module for processing GitHub webhook events, handling project onboarding, and issue event processing."""

import json
import logging
import os

from se_agent.change_suggester import suggest_changes
from se_agent.issue_analyzer import analyze_issue
from se_agent.localize.hierarchical import HierarchicalLocalizationStrategy
from se_agent.localize.semantic_vector_search import SemanticVectorSearchLocalizer
from se_agent.localize.localization_strategy import LocalizationStrategyType
from se_agent.project import Project
from se_agent.project_info import ProjectInfo
from se_agent.project_manager import ProjectManager

logger = logging.getLogger("se-agent")

IGNORE_TOKEN = "IGNORE"  # Token indicating an event should be ignored
TOP_N = int(os.getenv('TOP_N_FILES', 5))  # Number of top files to consider during localization
LOCALIZATION_STRATEGY = LocalizationStrategyType(
    os.getenv('LOCALIZATION_STRATEGY', LocalizationStrategyType.HIERARCHICAL)
)  # Localization strategy to use


def get_project_manager():
    """Retrieves the ProjectManager instance.

    Ensures that the projects store directory exists and initializes a ProjectManager.

    Returns:
        ProjectManager: An instance of the ProjectManager.
    """
    projects_store = os.getenv('PROJECTS_STORE')
    logger.debug(f"Projects store: {projects_store}")
    if not os.path.exists(projects_store):
        logger.debug(f"Creating: {projects_store}")
        os.makedirs(projects_store)
        logger.debug(f"Created: {projects_store}")
    return ProjectManager(projects_store)


def onboard_project(data, method):
    """Handles the onboarding of a new project.

    Args:
        data (dict): The project data used to create a ProjectInfo instance.
        method (str): The HTTP method used ('POST' or 'PUT').

    Returns:
        tuple: A tuple containing a status message dictionary and an HTTP status code.
    """
    if not data:
        return {'status': 'Invalid data'}, 400

    try:
        project_info = ProjectInfo(**data)
    except TypeError as e:
        return {'status': 'Invalid ProjectInfo structure', 'error': str(e)}, 400

    project_manager = get_project_manager()
    existing_project = project_manager.get_project(project_info.repo_full_name)

    if method == 'POST':
        if existing_project:
            return {'status': 'Project already exists'}, 409
        project_manager.add_project(project_info)

    # Proceed with onboarding (for both POST and PUT)
    try:
        github_token = os.getenv('GITHUB_TOKEN')
        project = Project(github_token, os.getenv('PROJECTS_STORE'), project_info)
        project.onboard()
        return {'status': 'Project onboarded successfully'}, 200
    except Exception as e:
        logger.exception("Error during project onboarding.")
        return {'status': 'Error onboarding project', 'error': str(e)}, 500


def process_webhook(data):
    """Processes GitHub webhook events.

    Handles issue creation, issue comment creation, and push events to the main branch.

    Args:
        data (dict): The webhook payload data from GitHub.

    Returns:
        tuple: A tuple containing a status message dictionary and an HTTP status code.
    """
    # Pretty print the received webhook payload
    print(json.dumps(data, indent=4))

    # Get project information from the webhook payload
    repo_full_name = data.get('repository').get('full_name')
    if not repo_full_name:
        return {'status': 'repository not found in payload'}, 400

    project_manager = get_project_manager()
    project_info = project_manager.get_project(repo_full_name)

    if project_info is None:
        return {'status': 'project not onboarded'}, 404

    github_token = os.getenv('GITHUB_TOKEN')
    project = Project(github_token, os.getenv('PROJECTS_STORE'), project_info)

    # Handle issue comment creation event
    if data.get('action') == 'created' and 'comment' in data and 'issue' in data:
        comment_details = data['comment']
        issue_details = data['issue']

        # Ignore comments on closed issues
        if issue_details.get('state') == 'closed':
            print("Ignoring comment on closed issue")
            return {'status': 'ignored comment on closed issue'}, 200

        result = process_issue_event(project, issue_details, comment_details)
        if result is not None:
            return {'status': 'Recommendations comment added to the issue'}, 200
        elif result == IGNORE_TOKEN:
            return {'status': 'ignored agent comment'}, 200
        else:
            return {'status': 'error processing comment'}, 500

    # Handle issue creation event
    if data.get('action') == 'opened' and 'issue' in data:
        issue_details = data['issue']
        result = process_issue_event(project, issue_details)
        if result is not None:
            return {'status': 'Recommendations comment added to the issue'}, 200
        else:
            return {'status': 'error processing issue'}, 500

    # Handle push event to main branch
    if data.get('ref') == f'refs/heads/{project.info.main_branch}' and data.get('commits'):
        try:
            modified_files = {
                os.path.relpath(file, project.info.src_folder)
                for commit in data['commits']
                for file in commit.get('modified', []) + commit.get('added', [])
                if file.startswith(project.info.src_folder) and file.endswith('.py')
            }
            if modified_files:  # Only update if there are code files
                project.update_codebase_understanding(modified_files)
                return {'status': 'Codebase understanding updated'}, 200
            else:
                logger.info("No code files changed in push event.")
                return {'status': 'No code files changed'}, 200
        except Exception as e:
            logger.exception("Error updating codebase understanding.")
            return {'status': 'error updating codebase understanding'}, 500

    return {'status': 'ignored event'}, 200


def process_issue_event(project: Project, issue_details, comment_details=None):
    """Processes new issues and issue comments.

    Analyzes the issue, localizes relevant code, and suggests changes.

    Args:
        project (Project): The project instance.
        issue_details (dict): Details of the GitHub issue.
        comment_details (dict, optional): Details of the comment if applicable.

    Returns:
        str or None: The change suggestions if successful, IGNORE_TOKEN if ignored, or None if an error occurred.
    """
    # Check if the comment is made by the agent itself to prevent infinite loops
    if comment_details:
        comment_body = comment_details.get('body', '')

        # Ignore comments that are from the agent itself
        if '<!-- SE Agent -->' in comment_body:
            print("Ignoring agent's own comment")
            return IGNORE_TOKEN

    # Choose localization strategy based on environment or project configuration
    if LOCALIZATION_STRATEGY == LocalizationStrategyType.SEMANTIC_VECTOR_SEARCH:
        localizationStrategy = SemanticVectorSearchLocalizer(project.get_vector_store())
    else:
        localizationStrategy = HierarchicalLocalizationStrategy(project)

    # Analyze the issue, localize relevant code files, and generate change suggestions
    try:
        analysis_results = analyze_issue(project, issue_details)
        logger.debug(f"Analysis results: {analysis_results}")
        filepaths = localizationStrategy.localize(issue=analysis_results, top_n=TOP_N)
        logger.debug(f"Localization results: {filepaths}")
        change_suggestions = suggest_changes(project, analysis_results, filepaths)
        logger.debug(f"Change suggestions: {change_suggestions}")
    except Exception as e:
        logger.exception("Error processing issue.")
        return None

    # Get the issue number from the issue details
    issue_number = issue_details['number']

    # Post the change suggestions as a comment on the GitHub issue
    try:
        # Include a special marker to identify the agent's own comments
        agent_comment = f"<!-- SE Agent -->\n{change_suggestions}"
        project.post_issue_comment(issue_number, agent_comment)
    except Exception as e:
        logger.exception("Error posting comment to GitHub.")
        return None

    return change_suggestions