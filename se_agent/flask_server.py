from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
from se_agent.listener_core import onboard_project, process_webhook

app = Flask(__name__)
CORS(app, resources={r"/onboard": {"origins": "*"}})

@app.route('/onboard', methods=['POST', 'PUT'])
def onboard_project_route():
    data = request.json
    response, status_code = onboard_project(data, request.method)
    return jsonify(response), status_code

@app.route('/webhook', methods=['POST'])
def webhook_route():
    data = request.json
    response, status_code = process_webhook(data)
    return jsonify(response), status_code

if __name__ == '__main__':
    """
    Runs the Flask server to listen for onboarding and GitHub webhook events.
    """
    app.run(host='0.0.0.0', port=3000)