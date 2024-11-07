import json
import os
import logging
logger = logging.getLogger("se-agent")

from se_agent.issue_analyzer import analyze_issue
from se_agent.change_suggester import suggest_changes
from se_agent.localizer import localize_issue
from se_agent.project import Project
from se_agent.project_info import ProjectInfo
from se_agent.project_manager import ProjectManager

IGNORE_TOKEN = "IGNORE"

def get_project_manager():
    projects_store = os.getenv('PROJECTS_STORE')
    logger.debug(f"Projects store: {projects_store}")
    if not os.path.exists(projects_store):
        logger.debug(f"Creating: {projects_store}")
        os.makedirs(projects_store)
        logger.debug(f"Created: {projects_store}")
    return ProjectManager(projects_store)

def onboard_project(data, method):
    """
    Handles the onboarding of a new project.
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
    """
    Processes GitHub webhook events.
    """
    # pretty print the data received in a well formatted way
    print(json.dumps(data, indent=4))

    # get project information
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

    # Handle push event to master branch
    if data.get('ref') == f'refs/heads/{project.info.main_branch}' and data.get('commits'):
        try:
            modified_files = {
                os.path.relpath(file, project.info.src_folder)
                for commit in data['commits']
                for file in commit.get('modified', []) + commit.get('added', [])
                if file.startswith(project.info.src_folder)
            }
            project.update_codebase_understanding(modified_files)
            return {'status': 'Codebase understanding updated'}, 200
        except Exception as e:
            logger.exception("Error updating codebase understanding.")
            return {'status': 'error updating codebase understanding'}, 500

    return {'status': 'ignored event'}, 200

def process_issue_event(project: Project, issue_details, comment_details=None):
    """
    Processes new issues and issue comments.
    """
    # Check if the comment is made by the agent itself
    if comment_details:
        comment_body = comment_details.get('body', '')
        
        # Ignore comments that are from the agent itself
        if '<!-- SE Agent -->' in comment_body:
            print("Ignoring agent's own comment")
            return IGNORE_TOKEN
        
        # Ignore comments that close the issue
        closing_keywords = ["fixes", "resolves", "closes"]
        if any(keyword in comment_body.lower() for keyword in closing_keywords):
            print("Ignoring comment that closes the issue")
            return IGNORE_TOKEN

    # Analyze, localize, and suggest changes for the issue
    try:
        analysis_results = analyze_issue(project, issue_details)
        logger.debug(f"Analysis results: {analysis_results}")
        localization_results = localize_issue(project, issue_details, analysis_results)
        logger.debug(f"Localization results: {localization_results}")
        change_suggestions = suggest_changes(project, analysis_results, localization_results)
        logger.debug(f"Change suggestions: {change_suggestions}")
    except Exception as e:
        logger.exception("Error processing issue.")
        return None

    # Get the issue number
    issue_number = issue_details['number']

    # Post the change suggestions as a comment on the GitHub issue
    try:
        # Include the special marker to identify agent's own comments
        agent_comment = f"<!-- SE Agent -->\n{change_suggestions}"
        project.post_issue_comment(issue_number, agent_comment)
    except Exception as e:
        logger.exception("Error posting comment to GitHub.")
        return None

    return change_suggestions
