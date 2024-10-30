import json
import logging
import os

from flask import Flask, request, jsonify

from se_agent.issue_analyzer import analyze_issue
from se_agent.change_suggester import suggest_changes
from se_agent.localizer import localize_issue
from se_agent.project import Project
from se_agent.project_info import ProjectInfo
from se_agent.project_manager import ProjectManager

app = Flask(__name__)

IGNORE_TOKEN = "IGNORE"

logger = logging.getLogger('se-agent')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
logger.addHandler(handler)

def get_project_manager():
    projects_store = os.getenv('PROJECTS_STORE')
    if not os.path.exists(projects_store):
        os.makedirs(projects_store)
    return ProjectManager(projects_store)

@app.route('/onboard', methods=['POST', 'PUT'])
def onboard_project():
    """
    Endpoint to onboard a new project or refresh an existing project.
    """
    data = request.json
    if not data:
        return jsonify({'status': 'Invalid data'}), 400

    try:
        project_info = ProjectInfo(**data)
    except TypeError as e:
        return jsonify({'status': 'Invalid ProjectInfo structure', 'error': str(e)}), 400

    project_manager = get_project_manager()
    existing_project = project_manager.get_project(project_info.repo_full_name)

    if request.method == 'POST':
        if existing_project:
            return jsonify({'status': 'Project already exists'}), 409
        project_manager.add_project(project_info)

    # Proceed with onboarding (for both POST and PUT)
    try:
        github_token = os.getenv('GITHUB_TOKEN')
        project = Project(github_token, os.getenv('PROJECTS_STORE'), project_info)
        project.onboard()
        return jsonify({'status': 'Project onboarded successfully'}), 200
    except Exception as e:
        logger.exception("Error during project onboarding.")
        return jsonify({'status': 'Error onboarding project', 'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint to receive GitHub webhook events.
    """
    data = request.json
    # pretty print the data received in a well formatted way
    print(json.dumps(data, indent=4))

    # get project information
    repo_full_name = data.get('repository').get('full_name')
    if not repo_full_name:
        return jsonify({'status': 'repository not found in payload'}), 400

    project_manager = get_project_manager()
    project_info = project_manager.get_project(repo_full_name)

    if project_info is None:
        return jsonify({'status': 'project not onboarded'}), 404
    
    github_token = os.getenv('GITHUB_TOKEN')
    project = Project(github_token, os.getenv('PROJECTS_STORE'), project_info)

    # Handle issue comment creation event
    if data.get('action') == 'created' and 'comment' in data and 'issue' in data:
        comment_details = data['comment']
        issue_details = data['issue']
        result = process_issue_event(project, issue_details, comment_details)
        if result is not None:
            return jsonify({'status': 'Recommendations comment added to the issue'}), 200
        elif result == IGNORE_TOKEN:
            return jsonify({'status': 'ignored agent comment'}), 200
        else:
            return jsonify({'status': 'error processing comment'}), 500

    # Handle issue creation event
    if data.get('action') == 'opened' and 'issue' in data:
        issue_details = data['issue']
        result = process_issue_event(project, issue_details)
        if result is not None:
            return jsonify({'status': 'Recommendations comment added to the issue'}), 200
        else:
            return jsonify({'status': 'error processing issue'}), 500

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
            return jsonify({'status': 'Codebase understanding updated'}), 200
        except Exception as e:
            logger.exception("Error updating codebase understanding.")
            return jsonify({'status': 'error updating codebase understanding'}), 500

    return jsonify({'status': 'ignored event'}), 200

def process_issue_event(project: Project, issue_details, comment_details=None):
    """
    Processes new issues and issue comments.
    """
    # Check if the comment is made by the agent itself
    if comment_details:
        if '<!-- SE Agent -->' in comment_details.get('body', ''):
            print("Ignoring agent's own comment")
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

def run_server():
    """
    Runs the Flask server to listen for GitHub webhooks.
    """
    app.run(host='0.0.0.0', port=3000)