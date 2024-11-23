"""Module for analyzing GitHub issues and extracting relevant information."""

from se_agent.project import Project

def analyze_issue(project: Project, issue_details):
    """Analyzes the issue to extract relevant information, including the conversation thread.

    Args:
        project (Project): The project instance used to fetch issue comments.
        issue_details (dict): Details of the GitHub issue.

    Returns:
        dict: A dictionary containing the issue's title, description, and conversation messages.
    """
    
    # Collect the conversation messages
    conversation = []

    # Include the issue title and body as the first message content
    conversation.append({
        'role': 'user',
        'content': f'Issue: {issue_details["title"]}\n\nDescription: {issue_details["body"]}'
    })

    # Fetch the comments on the issue
    issue_number = issue_details['number']
    try:
        comments = project.fetch_issue_comments(issue_number)
        for comment in comments:
            # Determine role based on the presence of '<!-- SE Agent -->' in the comment body
            if '<!-- SE Agent -->' in comment['body']:
                role = 'assistant'
            else:
                role = 'user'
            # Append the comment to the conversation
            conversation.append({'role': role, 'content': comment['body']})
    except Exception as e:
        print(f"Error fetching comments: {e}")
        # Proceed with just the issue title and body

    # Prepare analysis_results, including the conversation
    analysis_results = {
        'title': issue_details['title'],
        'description': issue_details['body'],
        'conversation': conversation
    }

    return analysis_results