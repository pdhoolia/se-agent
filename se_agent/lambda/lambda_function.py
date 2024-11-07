import os

from dotenv import load_dotenv
load_dotenv()

import json
from se_agent.listener_core import onboard_project, process_webhook

import logging
logger = logging.getLogger("se-agent")

# Set HOME to EFS backed path (may be used by git command)
os.environ["HOME"] = os.getenv("PROJECTS_STORE")

def handler(event, context):
    """Lambda function wrapper to listen for onboarding and GitHub webhook events."""
    
    path = event['rawPath']
    method = event['requestContext']['http']['method']
    data = json.loads(event['body']) if 'body' in event else {}

    logger.debug(f"Received event: {path} {method} {data}")

    if path == '/onboard' and method in ['POST', 'PUT']:
        logger.debug(f"Received onboard event")
        response, status_code = onboard_project(data, method)
    elif path == '/webhook' and method == 'POST':
        logger.debug(f"Received webhook event")
        response, status_code = process_webhook(data)
    else:
        response, status_code = {'status': 'ignored event'}, 200

    return {
        'statusCode': status_code,
        'body': json.dumps(response)
    }